import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db
import pipeline


def test_run_pipeline_success_updates_call_and_deletes_audio(tmp_path, monkeypatch):
    db_path = str(tmp_path / 'test.db')
    db.init_db(db_path)
    audio_path = tmp_path / 'call.webm'
    audio_path.write_bytes(b'fake-audio')

    call_id = db.create_call('Acme Co', None, 'free', audio_kept=False, audio_path=str(audio_path), db_path=db_path)

    monkeypatch.setattr(pipeline.transcription, 'transcribe', lambda path, tier: 'transcript text')
    monkeypatch.setattr(pipeline.summarization, 'summarize', lambda transcript, tier: {'budget': 'value'})

    pipeline.run_pipeline(call_id, str(audio_path), 'free', keep_audio=False, db_path=db_path)

    record = db.get_call(call_id, db_path=db_path)
    assert record['status'] == 'done'
    assert record['transcript'] == 'transcript text'
    assert record['summary_json'] == {'budget': 'value'}
    assert not audio_path.exists()


def test_run_pipeline_keeps_audio_when_requested(tmp_path, monkeypatch):
    db_path = str(tmp_path / 'test.db')
    db.init_db(db_path)
    audio_path = tmp_path / 'call.webm'
    audio_path.write_bytes(b'fake-audio')

    call_id = db.create_call('Acme Co', None, 'free', audio_kept=True, audio_path=str(audio_path), db_path=db_path)

    monkeypatch.setattr(pipeline.transcription, 'transcribe', lambda path, tier: 'transcript text')
    monkeypatch.setattr(pipeline.summarization, 'summarize', lambda transcript, tier: {'budget': 'value'})

    pipeline.run_pipeline(call_id, str(audio_path), 'free', keep_audio=True, db_path=db_path)

    assert audio_path.exists()


def test_run_pipeline_failure_sets_status_failed(tmp_path, monkeypatch):
    db_path = str(tmp_path / 'test.db')
    db.init_db(db_path)
    audio_path = tmp_path / 'call.webm'
    audio_path.write_bytes(b'fake-audio')

    call_id = db.create_call('Acme Co', None, 'free', audio_kept=False, audio_path=str(audio_path), db_path=db_path)

    def boom(path, tier):
        raise RuntimeError('whisper crashed')

    monkeypatch.setattr(pipeline.transcription, 'transcribe', boom)

    pipeline.run_pipeline(call_id, str(audio_path), 'free', keep_audio=False, db_path=db_path)

    record = db.get_call(call_id, db_path=db_path)
    assert record['status'] == 'failed'
    assert 'whisper crashed' in record['error_message']
