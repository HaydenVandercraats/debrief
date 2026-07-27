import json
import sqlite3
from datetime import datetime, timezone

DB_PATH = 'debrief.db'


def _resolve_path(db_path):
    return db_path if db_path is not None else DB_PATH


def get_connection(db_path=None):
    conn = sqlite3.connect(_resolve_path(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=None):
    conn = get_connection(db_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            company TEXT,
            contact_name TEXT,
            tier_used TEXT NOT NULL,
            audio_kept INTEGER NOT NULL DEFAULT 0,
            audio_path TEXT,
            transcript TEXT,
            summary_json TEXT,
            status TEXT NOT NULL,
            error_message TEXT
        )
    ''')
    conn.commit()
    conn.close()


def create_call(company, contact_name, tier_used, audio_kept, audio_path=None, db_path=None):
    conn = get_connection(db_path)
    created_at = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        '''INSERT INTO calls
           (created_at, company, contact_name, tier_used, audio_kept, audio_path, status)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (created_at, company, contact_name, tier_used, int(audio_kept), audio_path, 'transcribing'),
    )
    conn.commit()
    call_id = cursor.lastrowid
    conn.close()
    return call_id


def update_call(call_id, db_path=None, **fields):
    if not fields:
        return
    columns = ', '.join(f'{key} = ?' for key in fields)
    values = list(fields.values()) + [call_id]
    conn = get_connection(db_path)
    conn.execute(f'UPDATE calls SET {columns} WHERE id = ?', values)
    conn.commit()
    conn.close()


def get_call(call_id, db_path=None):
    conn = get_connection(db_path)
    row = conn.execute('SELECT * FROM calls WHERE id = ?', (call_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    result = dict(row)
    if result['summary_json']:
        result['summary_json'] = json.loads(result['summary_json'])
    return result


def list_calls(db_path=None):
    conn = get_connection(db_path)
    rows = conn.execute(
        'SELECT id, created_at, company, contact_name, status, tier_used FROM calls ORDER BY id DESC'
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
