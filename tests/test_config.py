import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


def test_load_config_returns_none_when_missing(tmp_path):
    assert config.load_config(data_dir=str(tmp_path)) is None


def test_save_and_load_config_round_trips(tmp_path):
    data_dir = str(tmp_path)
    config.save_config('hunter2', 'a' * 64, data_dir=data_dir)

    loaded = config.load_config(data_dir=data_dir)
    assert loaded is not None
    assert loaded['secret_key'] == 'a' * 64
    assert loaded['password_hash'] != 'hunter2'  # never stored in plaintext
    assert loaded['password_hash'].startswith('pbkdf2:') or ':' in loaded['password_hash']


def test_load_config_returns_none_for_corrupted_file(tmp_path):
    data_dir = str(tmp_path)
    config_path = os.path.join(data_dir, 'config.json')
    with open(config_path, 'w') as f:
        f.write('{not valid json')

    assert config.load_config(data_dir=data_dir) is None


def test_load_config_returns_none_when_incomplete(tmp_path):
    data_dir = str(tmp_path)
    config_path = os.path.join(data_dir, 'config.json')
    with open(config_path, 'w') as f:
        json.dump({'password_hash': 'only-this-key'}, f)

    assert config.load_config(data_dir=data_dir) is None


def test_get_data_dir_creates_directory(tmp_path, monkeypatch):
    target = str(tmp_path / 'Debrief')
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    result = config.get_data_dir()
    assert result == target
    assert os.path.isdir(target)


def test_load_config_returns_none_for_non_dict_json_null(tmp_path):
    data_dir = str(tmp_path)
    config_path = os.path.join(data_dir, 'config.json')
    with open(config_path, 'w') as f:
        json.dump(None, f)

    assert config.load_config(data_dir=data_dir) is None


def test_load_config_returns_none_for_non_dict_json_int(tmp_path):
    data_dir = str(tmp_path)
    config_path = os.path.join(data_dir, 'config.json')
    with open(config_path, 'w') as f:
        json.dump(42, f)

    assert config.load_config(data_dir=data_dir) is None


def test_load_config_returns_none_for_non_dict_json_list(tmp_path):
    data_dir = str(tmp_path)
    config_path = os.path.join(data_dir, 'config.json')
    with open(config_path, 'w') as f:
        json.dump([1, 2, 3], f)

    assert config.load_config(data_dir=data_dir) is None
