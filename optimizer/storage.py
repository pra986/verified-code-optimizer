import json
import sqlite3
import time
import uuid
from pathlib import Path
from .runner import RunError

class Reports:
    def __init__(self,directory):
        Path(directory).mkdir(parents=True,exist_ok=True);self.path=Path(directory)/'reports.sqlite3'
        with sqlite3.connect(self.path) as conn:conn.execute('CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY,created REAL NOT NULL,data TEXT NOT NULL)')
    def save(self,report):
        record=dict(report,id=uuid.uuid4().hex,created_at=time.time())
        with sqlite3.connect(self.path) as conn:conn.execute('INSERT INTO reports VALUES(?,?,?)',(record['id'],record['created_at'],json.dumps(record)))
        return record
    def get(self,identifier):
        with sqlite3.connect(self.path) as conn:row=conn.execute('SELECT data FROM reports WHERE id=?',(identifier,)).fetchone()
        if not row:raise RunError('Report not found.',404)
        return json.loads(row[0])
    def recent(self):
        with sqlite3.connect(self.path) as conn:rows=conn.execute('SELECT data FROM reports ORDER BY created DESC LIMIT 20').fetchall()
        return [{key:r[key] for key in ('id','candidate','n','status','created_at')} for r in [json.loads(row[0]) for row in rows]]
