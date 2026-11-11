"""SQLite durable metadata; one application instance. Restart interrupts active runs."""
import asyncio
import json
import logging
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from .database import connect
from ..contracts.errors import PublicError
from concurrent.futures import ThreadPoolExecutor


class JobManager:
    def __init__(self,path,workers=2,capacity=16,ttl=900):
        self.path=str(path);self.capacity=capacity;self.ttl=ttl
        self.pool=ThreadPoolExecutor(max_workers=workers,thread_name_prefix='hkeli-run')
        self.lock=threading.Lock();self.events={}
        with self.db() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,owner TEXT,status TEXT,created REAL,expires REAL,result TEXT,trace TEXT);
            CREATE TABLE IF NOT EXISTS audit(run_id TEXT,event TEXT,recorded REAL);''')
            db.execute("UPDATE jobs SET status='interrupted',result=? WHERE status IN ('pending','running')",
                       (json.dumps({'message':'Application restarted; submit again. No silent replay.'}),))

    @contextmanager
    def db(self):
        with connect(self.path) as db:
            db.execute('PRAGMA journal_mode=WAL')
            yield db

    def submit(self,owner,function):
        with self.lock,self.db() as db:
            db.execute('DELETE FROM jobs WHERE expires<? AND status NOT IN (\'pending\',\'running\')',(time.time(),))
            db.execute("DELETE FROM jobs WHERE id IN (SELECT id FROM jobs WHERE status NOT IN ('pending','running') ORDER BY created DESC LIMIT -1 OFFSET 255)")
            if db.execute("SELECT count(*) FROM jobs WHERE status IN ('pending','running')").fetchone()[0]>=self.capacity:raise OverflowError('Execution capacity busy.')
            key=uuid.uuid4().hex;event=threading.Event();self.events[key]=event
            db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?)',(key,owner,'pending',time.time(),time.time()+self.ttl,None,'[]'))
        self.pool.submit(self._run,key,function,event)
        return key

    def progress(self,key,task,status):
        with self.lock,self.db() as db:
            row=db.execute('SELECT trace FROM jobs WHERE id=?',(key,)).fetchone()
            if not row:return
            trace=json.loads(row[0]);trace.append({'task':task,'status':status,'time':time.time()})
            db.execute('UPDATE jobs SET trace=? WHERE id=?',(json.dumps(trace),key))

    def _run(self,key,function,event):
        started=time.monotonic()
        with self.db() as db:db.execute("UPDATE jobs SET status='running' WHERE id=?",(key,))
        try:
            result=asyncio.run(function(key,event,lambda task,status:self.progress(key,task,status)))
            status='cancelled' if event.is_set() else 'completed'
        except asyncio.CancelledError:status,result='cancelled',{'message':'Run cancelled.'}
        except PermissionError:status,result='failed',{'code':'access_denied','message':'Requested resource or skill is not authorized.'}
        except TimeoutError:status,result='failed',{'code':'timeout','message':'Execution deadline reached; no substitute financial claim produced.'}
        except PublicError as error:status,result='failed',{'code':error.code,'message':str(error)}
        except Exception as error:
            status,result='failed',{'code':'execution_failed','message':'Execution failed: '+type(error).__name__+'. Inspect sanitized task trace.'}
            logging.getLogger('hkeli').error(json.dumps({'run_id':key,'error_type':type(error).__name__}))
        serialized=json.dumps(result)
        if len(serialized)>2000000:
            status='failed';serialized=json.dumps({'code':'result_capacity','message':'Result state capacity exceeded; narrow the authorized scope. No partial totals returned.'})
        with self.lock,self.db() as db:
            db.execute('UPDATE jobs SET status=?,result=? WHERE id=?',(status,serialized,key))
            db.execute('INSERT INTO audit VALUES (?,?,?)',(key,json.dumps({'status':status,'latency_seconds':time.monotonic()-started}),time.time()))
            self.events.pop(key,None)

    def get(self,owner,key):
        with self.db() as db:row=db.execute('SELECT status,expires,result,trace FROM jobs WHERE id=? AND owner=?',(key,owner)).fetchone()
        if not row or row[1]<time.time():raise KeyError('Run absent or expired.')
        out={'run_id':key,'status':row[0],'trace':json.loads(row[3])}
        if row[2]:out['answer' if row[0]=='completed' else 'error']=json.loads(row[2])
        return out

    def cancel(self,owner,key):
        self.get(owner,key)
        with self.lock:
            event=self.events.get(key)
            if event:event.set()
        return {'status':'cancellation_requested' if event else 'already_terminal'}

    def close(self):
        with self.lock:
            for event in self.events.values():event.set()
        self.pool.shutdown(wait=True,cancel_futures=True)
