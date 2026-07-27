import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_setup_returns_404_when_not_frozen(client):
    response = client.get('/setup')
    assert response.status_code == 404


def test_setup_page_and_flow_when_frozen(tmp_path, monkeypatch):
    monkeypatch.setenv('DEBRIEF_PASSWORD', 'unused-in-frozen-mode')
    monkeypatch.setenv('SECRET_KEY', 'unused-in-frozen-mode')
    monkeypatch.setenv('DEBRIEF_TIER', 'free')

    import db
    db.DB_PATH = str(tmp_path / 'test.db')
    db.init_db(db.DB_PATH)

    import importlib
    import app as app_module
    importlib.reload(app_module)

    app_module.FROZEN = True
    monkeypatch.setattr(app_module.cfg, 'get_data_dir', lambda: str(tmp_path))

    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as client:
        # Before setup: index redirects to /setup, not /login
        response = client.get('/', follow_redirects=False)
        assert response.status_code == 302
        assert '/setup' in response.headers['Location']

        # GET /setup renders the form
        response = client.get('/setup')
        assert response.status_code == 200
        assert b'password' in response.data.lower()

        # POST /setup with empty password shows an error, doesn't create config
        response = client.post('/setup', data={'password': ''})
        assert response.status_code == 200
        assert b'required' in response.data.lower()
        assert app_module.cfg.load_config(data_dir=str(tmp_path)) is None

        # POST /setup with a real password creates config and redirects to /login
        response = client.post('/setup', data={'password': 'hunter2'}, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers['Location'].endswith('/login')
        stored = app_module.cfg.load_config(data_dir=str(tmp_path))
        assert stored is not None

        # Now / redirects to /login, not /setup
        response = client.get('/', follow_redirects=False)
        assert '/login' in response.headers['Location']

        # Wrong password fails
        response = client.post('/login', data={'password': 'wrong'})
        assert b'Incorrect password' in response.data

        # Right password succeeds
        response = client.post('/login', data={'password': 'hunter2'}, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers['Location'].endswith('/')


def test_setup_get_redirects_to_login_when_already_configured(tmp_path, monkeypatch):
    import importlib
    import app as app_module
    importlib.reload(app_module)

    app_module.FROZEN = True
    monkeypatch.setattr(app_module.cfg, 'get_data_dir', lambda: str(tmp_path))
    app_module.cfg.save_config('hunter2', 'a' * 64, data_dir=str(tmp_path))

    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as client:
        response = client.get('/setup', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.headers['Location']
