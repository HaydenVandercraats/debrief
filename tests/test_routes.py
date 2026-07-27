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
