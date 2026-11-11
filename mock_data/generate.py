"""Reproducible synthetic business database. Never merges with live identifiers."""
import sqlite3
from pathlib import Path
from datetime import date, timedelta
from hk_platform.runtime.database import connect

VERSION = 'synthetic-1.0'
AS_OF = '2026-10-15'


def initialize(path, rows=120):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS metadata(version TEXT, as_of TEXT);
        CREATE TABLE IF NOT EXISTS positions(id TEXT PRIMARY KEY,client TEXT,branch TEXT,district TEXT,country TEXT,
          product TEXT,underlying TEXT,sector TEXT,currency TEXT,notional INTEGER,coupon REAL,maturity TEXT,
          snapshot TEXT,worst_of INTEGER,ki_flag INTEGER,ko_flag INTEGER);
        CREATE TABLE IF NOT EXISTS sales(id TEXT PRIMARY KEY,client TEXT,branch TEXT,country TEXT,
          currency TEXT,amount INTEGER,revenue INTEGER,trade_date TEXT,channel TEXT);
        CREATE TABLE IF NOT EXISTS rfqs(id TEXT,client TEXT,country TEXT,status TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS customers(id TEXT PRIMARY KEY,country TEXT,segment TEXT,branch TEXT);
        CREATE TABLE IF NOT EXISTS engagement(id TEXT PRIMARY KEY,client TEXT,country TEXT,kind TEXT,event_date TEXT);
        CREATE TABLE IF NOT EXISTS maturities(position_id TEXT,maturity TEXT,country TEXT);
        CREATE TABLE IF NOT EXISTS rollovers(position_id TEXT,country TEXT,eligible INTEGER,status TEXT);
        CREATE TABLE IF NOT EXISTS branches(id TEXT,district TEXT,valid_from TEXT,valid_to TEXT);
        CREATE TABLE IF NOT EXISTS channel_events(id TEXT,client TEXT,country TEXT,stage TEXT,event_date TEXT);
        CREATE TABLE IF NOT EXISTS market(symbol TEXT,price REAL,observed TEXT,currency TEXT);
        CREATE TABLE IF NOT EXISTS products(id TEXT,name TEXT,basket TEXT);
        CREATE TABLE IF NOT EXISTS thresholds(metric TEXT,limit_value REAL,version TEXT);
        ''')
        if db.execute('SELECT count(*) FROM metadata').fetchone()[0]: return
        db.execute('INSERT INTO metadata VALUES (?,?)', (VERSION, AS_OF))
        for i in range(rows):
            client, branch = f'SYN-C{i%30:03}', f'SYN-B{i%6}'
            country = 'SG' if i%11 == 0 else 'HK'
            currency = 'USD' if i%13 == 0 else 'HKD'
            maturity = None if i%31 == 0 else (date.fromisoformat(AS_OF)+timedelta(days=i%40)).isoformat()
            pid = f'SYN-P{i:06}'
            db.execute('INSERT INTO positions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (pid,client,branch,f'SYN-D{i%3}',country,f'SYN-PRODUCT{i%3}',f'SYN-STOCK{i%12}',
                        f'SYN-SECTOR{i%4}',currency,(i%10+1)*100000,4+(i%9)/2,maturity,AS_OF,int(i%3==0),int(i%17==0),int(i%19==0)))
            db.execute('INSERT INTO sales VALUES (?,?,?,?,?,?,?,?,?)',
                       (f'SYN-T{i}',client,branch,country,currency,(i%8+1)*100000,(i%8+1)*1000,
                        (date.fromisoformat(AS_OF)-timedelta(days=i%28)).isoformat(),'digital' if i%2 else 'branch'))
            rfq=(f'SYN-R{i}',client,country,'won' if i%3==0 else 'open',(date.fromisoformat(AS_OF)-timedelta(days=i%28)).isoformat())
            db.execute('INSERT INTO rfqs VALUES (?,?,?,?,?)',rfq)
            if i%10==0: db.execute('INSERT INTO rfqs VALUES (?,?,?,?,?)',rfq)
            db.execute('INSERT OR IGNORE INTO customers VALUES (?,?,?,?)',(client,country,'PB' if i%2 else 'Treasury',branch))
            db.execute('INSERT INTO engagement VALUES (?,?,?,?,?)',(f'SYN-E{i}',client,country,'meeting' if i%2 else 'call',AS_OF))
            db.execute('INSERT INTO maturities VALUES (?,?,?)',(pid,maturity,country))
            db.execute('INSERT INTO rollovers VALUES (?,?,?,?)',(pid,country,int(i%2==0),'review'))
            for stage in ('visit','quote')+ (('trade',) if i%3==0 else ()):
                db.execute('INSERT INTO channel_events VALUES (?,?,?,?,?)',(f'SYN-J{i}-{stage}',client,country,stage,AS_OF))
        db.executemany('INSERT INTO branches VALUES (?,?,?,?)',[(f'SYN-B{i}',f'SYN-D{i%3}','2020-01-01','2099-12-31') for i in range(6)])
        db.execute("INSERT INTO branches VALUES ('SYN-B0','SYN-OLD','2010-01-01','2019-12-31')")
        db.executemany('INSERT INTO market VALUES (?,?,?,?)',[(f'SYN-STOCK{i}',100+i,'2020-01-01' if i==0 else AS_OF,'HKD') for i in range(12)])
        db.execute("INSERT INTO products VALUES ('SYN-PRODUCT0','Synthetic worst-of ELI','SYN-STOCK0,SYN-STOCK1')")
        db.execute("INSERT INTO thresholds VALUES ('concentration_share',0.10,'synthetic-1.0')")


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--path',default='var/business.sqlite');parser.add_argument('--rows',type=int,default=120)
    args=parser.parse_args();initialize(args.path,args.rows)
