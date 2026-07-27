import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db


def test_create_and_get_call(tmp_path):
    db_path = str(tmp_path / 'test.db')
    db.init_db(db_path)

    call_id = db.create_call(
        company='Acme Co',
        contact_name='Jordan Lee',
        tier_used='free',
        audio_kept=False,
        db_path=db_path,
    )

    record = db.get_call(call_id, db_path=db_path)
    assert record['company'] == 'Acme Co'
    assert record['contact_name'] == 'Jordan Lee'
    assert record['tier_used'] == 'free'
    assert record['audio_kept'] == 0
    assert record['audio_path'] is None
    assert record['status'] == 'transcribing'
    assert record['transcript'] is None
    assert record['summary_json'] is None
    assert record['error_message'] is None
    assert record['created_at'] is not None


def test_get_call_missing_returns_none(tmp_path):
    db_path = str(tmp_path / 'test.db')
    db.init_db(db_path)
    assert db.get_call(999, db_path=db_path) is None


def test_update_call_sets_fields(tmp_path):
    db_path = str(tmp_path / 'test.db')
    db.init_db(db_path)
    call_id = db.create_call('Acme Co', 'Jordan Lee', 'free', False, db_path=db_path)

    db.update_call(call_id, db_path=db_path, transcript='hello world', status='summarizing')
    record = db.get_call(call_id, db_path=db_path)
    assert record['transcript'] == 'hello world'
    assert record['status'] == 'summarizing'


def test_list_calls_orders_newest_first(tmp_path):
    db_path = str(tmp_path / 'test.db')
    db.init_db(db_path)
    first_id = db.create_call('First Co', None, 'free', False, db_path=db_path)
    second_id = db.create_call('Second Co', None, 'free', False, db_path=db_path)

    calls = db.list_calls(db_path=db_path)
    assert [c['id'] for c in calls] == [second_id, first_id]
