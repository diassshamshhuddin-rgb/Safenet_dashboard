"""Persistent local identity, audit and review storage."""
import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB = Path(os.environ.get('SAFENET_DB', Path(__file__).resolve().parents[1] / 'data/workspace.sqlite3'))

def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 310000).hex()
    return salt + ':' + digest

@contextmanager
def connection():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=20)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()

def init():
    with connection() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, login TEXT UNIQUE NOT NULL, password TEXT NOT NULL, department TEXT NOT NULL, role TEXT NOT NULL, active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER, expires REAL);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, user_id INTEGER, event TEXT, detail TEXT, time TEXT);
        CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY, case_id TEXT, user_id INTEGER, status TEXT, time TEXT);
        CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, user_id INTEGER, body TEXT, time TEXT);
        CREATE TABLE IF NOT EXISTS attempts(login TEXT PRIMARY KEY, count INTEGER DEFAULT 0, until REAL DEFAULT 0);
        ''')

def users():
    with connection() as db:
        return [dict(r) for r in db.execute('SELECT id,name,login,department,role,active FROM users ORDER BY id')]

def has_admin():
    return any(u['role']=='admin' for u in users())

def require(db, token, role=None):
    import time
    u = db.execute('SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token=? AND s.expires>? AND u.active=1', (token,time.time())).fetchone()
    if u is None or (role and u['role'] != role):
        raise PermissionError('access')
    return u

def current(token):
    with connection() as db:
        try:
            u=dict(require(db,token));u.pop('password');return u
        except PermissionError:
            return None

def add_user(name,login,password,department,token=None,bootstrap=False):
    login=login.strip().lower()
    if not all((name.strip(),login,department.strip())) or len(password)<10:
        raise ValueError('validation')
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        if bootstrap:
            if db.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():raise PermissionError('initialized')
        else:require(db,token,'admin')
        db.execute('INSERT INTO users(name,login,password,department,role) VALUES(?,?,?,?,?)',(name.strip(),login,password_hash(password),department.strip(),'admin' if bootstrap else 'analyst'))
        db.execute('INSERT INTO audit(user_id,event,detail,time) VALUES(?,?,?,?)',(None if bootstrap else require(db,token)['id'],'create',login,timestamp()))

def login(login,password,role):
    import time
    login=login.strip().lower()
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        a=db.execute('SELECT * FROM attempts WHERE login=?',(login,)).fetchone()
        if a and a['until']>time.time():return None
        u=db.execute('SELECT * FROM users WHERE login=? AND active=1',(login,)).fetchone()
        salt=(u['password'].split(':')[0] if u else 'invalid')
        valid=hmac.compare_digest(password_hash(password,salt),u['password'] if u else '')
        if not u or not valid or u['role']!=role:
            n=(a['count'] if a else 0)+1
            db.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?)',(login,n,time.time()+300 if n>=5 else 0))
            db.execute('INSERT INTO audit(event,detail,time) VALUES(?,?,?)',('failed_login',login,timestamp()))
            return None
        db.execute('DELETE FROM attempts WHERE login=?',(login,))
        token=secrets.token_urlsafe(32)
        db.execute('INSERT INTO sessions VALUES(?,?,?)',(token,u['id'],time.time()+8*3600))
        db.execute('INSERT INTO audit(user_id,event,detail,time) VALUES(?,?,?,?)',(u['id'],'login','',timestamp()))
        return token

def logout(token):
    with connection() as db:
        u=current(token)
        if u:db.execute('INSERT INTO audit(user_id,event,detail,time) VALUES(?,?,?,?)',(u['id'],'logout','',timestamp()))
        db.execute('DELETE FROM sessions WHERE token=?',(token,))

def deactivate(token,user_id):
    with connection() as db:
        admin=require(db,token,'admin')
        db.execute("UPDATE users SET active=0 WHERE id=? AND role='analyst'",(user_id,))
        db.execute('DELETE FROM sessions WHERE user_id=?',(user_id,))
        db.execute('INSERT INTO audit(user_id,event,detail,time) VALUES(?,?,?,?)',(admin['id'],'deactivate',str(user_id),timestamp()))

def decide(token,case_id,status):
    if status not in ('confirmed','false','more'):raise ValueError('status')
    with connection() as db:
        u=require(db,token,'analyst')
        db.execute('INSERT INTO decisions(case_id,user_id,status,time) VALUES(?,?,?,?)',(case_id,u['id'],status,timestamp()))

def reviews(token,personal=False):
    with connection() as db:
        u=require(db,token)
        return [dict(r) for r in db.execute('SELECT * FROM decisions'+(' WHERE user_id=?' if personal else '')+' ORDER BY id DESC',(u['id'],) if personal else ())]

def audit(token):
    with connection() as db:
        require(db,token,'admin')
        return [dict(r) for r in db.execute('SELECT a.time,u.login,a.event,a.detail FROM audit a LEFT JOIN users u ON a.user_id=u.id ORDER BY a.id DESC LIMIT 200')]

def messages(token,body=None):
    with connection() as db:
        u=require(db,token)
        if body and body.strip():db.execute('INSERT INTO messages(user_id,body,time) VALUES(?,?,?)',(u['id'],body.strip()[:4000],timestamp()))
        query='SELECT m.*,u.login FROM messages m JOIN users u ON u.id=m.user_id'
        return [dict(r) for r in db.execute(query+('' if u['role']=='admin' else ' WHERE user_id=?')+' ORDER BY m.id',( ) if u['role']=='admin' else (u['id'],))]
