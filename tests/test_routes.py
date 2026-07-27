import io


def test_upload_creates_call_and_redirects_to_detail(client, monkeypatch):
    client.post('/login', data={'password': 'test-password'})

    import app as app_module
    monkeypatch.setattr(app_module.pipeline, 'run_pipeline', lambda *a, **k: None)

    data = {
        'company': 'Acme Co',
        'contact_name': 'Jordan Lee',
        'keep_audio': '',
        'audio': (io.BytesIO(b'fake-audio-bytes'), 'call.webm'),
    }
    response = client.post('/calls', data=data, content_type='multipart/form-data', follow_redirects=False)

    assert response.status_code == 302
    assert '/calls/' in response.headers['Location']


def test_call_detail_shows_summary(client, monkeypatch):
    client.post('/login', data={'password': 'test-password'})

    import app as app_module
    import db

    def fake_run_pipeline(call_id, audio_path, tier, keep_audio, db_path=None):
        db.update_call(call_id, db_path=db_path, transcript='hello', summary_json='{"budget": "fifty grand"}', status='done')

    monkeypatch.setattr(app_module.pipeline, 'run_pipeline', fake_run_pipeline)

    data = {
        'company': 'Acme Co',
        'contact_name': '',
        'keep_audio': '',
        'audio': (io.BytesIO(b'fake-audio-bytes'), 'call.webm'),
    }
    upload_response = client.post('/calls', data=data, content_type='multipart/form-data')
    call_url = upload_response.headers['Location']

    detail_response = client.get(call_url)
    assert detail_response.status_code == 200
    assert b'fifty grand' in detail_response.data


def test_call_detail_404_for_missing_id(client):
    client.post('/login', data={'password': 'test-password'})
    response = client.get('/calls/999')
    assert response.status_code == 404


def test_retry_reruns_pipeline_when_audio_kept(client, monkeypatch, tmp_path):
    client.post('/login', data={'password': 'test-password'})

    import app as app_module
    import db

    audio_path = tmp_path / 'kept.webm'
    audio_path.write_bytes(b'fake-audio')
    call_id = db.create_call('Acme Co', None, 'free', audio_kept=True, audio_path=str(audio_path))
    db.update_call(call_id, status='failed', error_message='boom')

    calls_made = []
    monkeypatch.setattr(
        app_module.pipeline, 'run_pipeline',
        lambda cid, path, tier, keep_audio, **k: calls_made.append((cid, path, tier, keep_audio)),
    )

    response = client.post(f'/calls/{call_id}/retry', follow_redirects=False)
    assert response.status_code == 302
    assert calls_made == [(call_id, str(audio_path), 'free', True)]


def test_retry_returns_400_when_audio_not_kept(client):
    client.post('/login', data={'password': 'test-password'})

    import db
    call_id = db.create_call('Acme Co', None, 'free', audio_kept=False, audio_path=None)
    db.update_call(call_id, status='failed', error_message='boom')

    response = client.post(f'/calls/{call_id}/retry')
    assert response.status_code == 400
