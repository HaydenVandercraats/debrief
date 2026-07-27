import json
import os

from werkzeug.security import generate_password_hash


def get_data_dir():
    base = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
    data_dir = os.path.join(base, 'Debrief')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def _config_path(data_dir=None):
    resolved_dir = data_dir if data_dir is not None else get_data_dir()
    return os.path.join(resolved_dir, 'config.json')


def load_config(data_dir=None):
    path = _config_path(data_dir)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if 'password_hash' not in data or 'secret_key' not in data:
        return None
    return data


def save_config(password, secret_key, data_dir=None):
    data = {
        'password_hash': generate_password_hash(password),
        'secret_key': secret_key,
    }
    path = _config_path(data_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f)
    return data
