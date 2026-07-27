import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / 'test.db')
    upload_dir = str(tmp_path / 'uploads')
    monkeypatch.setenv('DEBRIEF_PASSWORD', 'test-password')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('DEBRIEF_TIER', 'free')
    monkeypatch.setenv('DEBRIEF_UPLOAD_DIR', upload_dir)

    import db
    monkeypatch.setattr(db, 'DB_PATH', db_path)
    db.init_db(db_path)

    import importlib
    import app as app_module
    importlib.reload(app_module)

    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as test_client:
        yield test_client
