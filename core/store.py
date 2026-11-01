import os
import sqlite3
from contextlib import closing


def _conn():
    c = sqlite3.connect(os.getenv("CIVICPILOT_DB", "civicpilot.db"))
    c.execute("create table if not exists applications (id integer primary key autoincrement, "
              "service text, application_id text, status text, submitted_at text)")
    return c


def save(service, application_id, status, submitted_at):
    with closing(_conn()) as c, c:
        c.execute("insert into applications (service, application_id, status, submitted_at) values (?,?,?,?)",
                  (service, application_id, status, submitted_at))


def update_status(application_id, status):
    with closing(_conn()) as c, c:
        c.execute("update applications set status = ? where application_id = ?", (status, application_id))


def history(limit=10):
    with closing(_conn()) as c:
        rows = c.execute("select service, application_id, status, submitted_at from applications "
                         "order by id desc limit ?", (limit,)).fetchall()
    return [dict(zip(("service", "application_id", "status", "submitted_at"), r)) for r in rows]
