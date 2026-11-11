"""Owned, expiring bounded result snapshots; no raw CSV, tokens or binary images."""
import json
import time
import uuid
from .database import connect


class Conversations:
    def __init__(self,path,ttl=86400):
        self.path=str(path);self.ttl=ttl
        with connect(self.path) as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,owner TEXT,created REAL,expires REAL);
            CREATE TABLE IF NOT EXISTS turns(id TEXT PRIMARY KEY,conversation TEXT,question TEXT,created REAL,run_id TEXT,status TEXT,answer TEXT);
            CREATE INDEX IF NOT EXISTS turns_conversation ON turns(conversation,created);''')
            db.execute("UPDATE turns SET status='interrupted' WHERE status='pending'")
        self.cleanup()

    def cleanup(self):
        with connect(self.path) as db:
            db.execute('DELETE FROM turns WHERE conversation IN (SELECT id FROM conversations WHERE expires<?)',(time.time(),))
            db.execute('DELETE FROM conversations WHERE expires<?',(time.time(),))

    def create(self,owner):
        self.cleanup();key=uuid.uuid4().hex
        with connect(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT count(*) FROM conversations WHERE owner=?',(owner,)).fetchone()[0]>=20:raise OverflowError('Conversation limit reached; delete an old chat.')
            if db.execute('SELECT count(*) FROM conversations').fetchone()[0]>=1000:raise OverflowError('Conversation capacity reached.')
            db.execute('INSERT INTO conversations VALUES (?,?,?,?)',(key,owner,time.time(),time.time()+self.ttl))
        return key

    def list(self,owner):
        with connect(self.path) as db:
            return [{'id':r[0],'created':r[1],'expires':r[2]} for r in db.execute('SELECT id,created,expires FROM conversations WHERE owner=? AND expires>? ORDER BY created DESC',(owner,time.time()))]

    def get(self,owner,key):
        with connect(self.path) as db:
            if not db.execute('SELECT 1 FROM conversations WHERE id=? AND owner=? AND expires>?',(key,owner,time.time())).fetchone():raise KeyError('Conversation absent or expired.')
            return [{'id':r[0],'question':r[1],'run_id':r[2],'status':r[3],'answer':json.loads(r[4]) if r[4] else None} for r in db.execute('SELECT id,question,run_id,status,answer FROM turns WHERE conversation=? ORDER BY created,rowid',(key,))]

    def begin(self,owner,key,question):
        self.get(owner,key);turn=uuid.uuid4().hex
        with connect(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM conversations WHERE id=? AND owner=? AND expires>?',(key,owner,time.time())).fetchone():raise KeyError('Conversation absent or expired.')
            if db.execute("SELECT 1 FROM turns WHERE conversation=? AND status='pending'",(key,)).fetchone():raise OverflowError('This chat already has an active request.')
            db.execute('INSERT INTO turns VALUES (?,?,?,?,?,?,?)',(turn,key,question,time.time(),None,'pending',None))
        return turn

    def bind(self,turn,run_id):
        with connect(self.path) as db:db.execute('UPDATE turns SET run_id=? WHERE id=?',(run_id,turn))

    def finish(self,turn,answer=None,status='completed'):
        serialized=json.dumps(answer) if answer is not None else None
        if serialized and len(serialized)>2000000:serialized=None;status='failed'
        with connect(self.path) as db:
            row=db.execute('SELECT conversation FROM turns WHERE id=?',(turn,)).fetchone()
            if not row:return
            db.execute('UPDATE turns SET status=?,answer=? WHERE id=?',(status,serialized,turn))
            records=db.execute('SELECT id,length(coalesce(answer,\'\')) FROM turns WHERE conversation=? ORDER BY created DESC,rowid DESC',(row[0],)).fetchall()
            total=0
            for index,(key,size) in enumerate(records):
                total+=size
                if index>=20 or total>8000000:db.execute('DELETE FROM turns WHERE id=? AND status!=\'pending\'',(key,))

    def delete(self,owner,key):
        self.get(owner,key)
        with connect(self.path) as db:
            if db.execute("SELECT 1 FROM turns WHERE conversation=? AND status='pending'",(key,)).fetchone():raise ValueError('Cancel the active request before deleting this chat.')
            db.execute('DELETE FROM turns WHERE conversation=?',(key,));db.execute('DELETE FROM conversations WHERE id=? AND owner=?',(key,owner))
