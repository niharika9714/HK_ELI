"""Transactions also close connections; sqlite3's own context manager does not."""
import sqlite3
from contextlib import contextmanager

@contextmanager
def connect(path,timeout=10):
    db=sqlite3.connect(str(path),timeout=timeout)
    try:
        with db:yield db
    finally:db.close()
