# Debrief Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package Debrief as a double-clickable Windows `debrief.exe` with a first-run password setup screen (no terminal/env-vars needed), and build a Designmodo-inspired static landing page that links to the download.

**Architecture:** A new `config.py` module handles a local JSON config file (`%LOCALAPPDATA%\Debrief\config.json`) holding a hashed password and a persistent `SECRET_KEY`, used only when the app is running as a PyInstaller-frozen executable (`sys.frozen`). `app.py` gains a `/setup` route and frozen-aware storage paths, gated entirely on `sys.frozen` so the existing env-var-based dev/test workflow is untouched. A `debrief.spec` PyInstaller file builds the exe. A separate `site/` static HTML/CSS/JS folder is the public marketing page, deployed independently to Render.

**Tech Stack:** Flask (existing), `werkzeug.security` (password hashing, already a Flask dependency), PyInstaller (new build-time dependency), plain HTML/CSS/vanilla JS for the site (no framework, no build step).

## Global Constraints

- Dev/test workflow (`python app.py`, `DEBRIEF_PASSWORD`/`SECRET_KEY` env vars) must continue working unchanged — all packaging behavior is gated on `sys.frozen` being true, which is only ever true inside a PyInstaller-built exe.
- Config file: `%LOCALAPPDATA%\Debrief\config.json`, containing exactly `{"password_hash": "<werkzeug hash>", "secret_key": "<64-char hex>"}`.
- A corrupted/unreadable config file must be treated as "no config" (fall back to `/setup`), never crash the app.
- The Whisper model itself is never bundled into the exe.
- Pro tier (`DEBRIEF_TIER=pro`) stays env-var-only — not part of `/setup` or the config file, in either packaging track.
- The static site has no framework/build step and no automated tests — manual browser verification only.
- No installer wizard/uninstaller in this pass — a single portable `debrief.exe` is the entire v1 packaging deliverable.

---

### Task 1: Local config module

**Files:**
- Create: `config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `config.get_data_dir() -> str` (creates and returns `%LOCALAPPDATA%\Debrief`, or `~/Debrief` if `LOCALAPPDATA` is unset), `config.load_config(data_dir=None) -> dict | None` (returns `{"password_hash": str, "secret_key": str}` or `None` if missing/corrupted/incomplete), `config.save_config(password, secret_key, data_dir=None) -> dict` (writes the config file, returns the written dict).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `config.py` doesn't exist.

- [ ] **Step 3: Implement `config.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: add local config module for packaged-app password/secret storage"
```

---

### Task 2: First-run setup route + frozen-aware auth in app.py

**Files:**
- Modify: `app.py`
- Create: `templates/setup.html`
- Test: `tests/test_setup.py`

**Interfaces:**
- Consumes: `config.load_config(data_dir=None)`, `config.save_config(password, secret_key, data_dir=None)`, `config.get_data_dir()` (Task 1).
- Produces: `app.FROZEN` (bool, `getattr(sys, 'frozen', False)`), route `setup` (`GET`/`POST` `/setup`), a `before_request` hook that redirects to `/setup` whenever `FROZEN` is true and no config exists yet.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_setup.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_setup.py -v`
Expected: FAIL — `/setup` route doesn't exist, `app.FROZEN`/`app.cfg` don't exist.

- [ ] **Step 3: Modify `app.py`**

Add near the top, after the existing imports:

```python
import sys
from werkzeug.security import check_password_hash

import config as cfg

FROZEN = getattr(sys, 'frozen', False)
```

Replace the existing `app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)` line with:

```python
if FROZEN:
    _existing_config = cfg.load_config()
    app.secret_key = _existing_config['secret_key'] if _existing_config else secrets.token_hex(32)
else:
    app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
```

Add the setup route and a before_request guard, placed above the existing `login_required` decorator:

```python
def setup_required():
    return FROZEN and cfg.load_config() is None


@app.before_request
def enforce_setup():
    if setup_required() and request.endpoint not in ('setup', 'static'):
        return redirect(url_for('setup'))


@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if not FROZEN:
        abort(404)
    if cfg.load_config() is not None:
        return redirect(url_for('login'))

    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        if not password:
            error = 'Password is required.'
        else:
            secret_key = secrets.token_hex(32)
            cfg.save_config(password, secret_key)
            app.secret_key = secret_key
            return redirect(url_for('login'))
    return render_template('setup.html', error=error)
```

Replace the body of the existing `login()` view's password-check block (the part that reads `os.environ.get('PRIMER_PASSWORD')`-style — actually `DEBRIEF_PASSWORD` per Task 2 of the v1 plan) with a branch on `FROZEN`:

```python
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        submitted = request.form.get('password', '')
        if FROZEN:
            stored = cfg.load_config()
            if stored is None:
                return redirect(url_for('setup'))
            valid = check_password_hash(stored['password_hash'], submitted)
        else:
            expected_password = os.environ.get('DEBRIEF_PASSWORD')
            if expected_password is None:
                error = 'Server misconfigured: DEBRIEF_PASSWORD is not set.'
                return render_template('login.html', error=error)
            valid = submitted == expected_password
        if valid:
            session['logged_in'] = True
            return redirect(url_for('index'))
        error = 'Incorrect password.'
    return render_template('login.html', error=error)
```

- [ ] **Step 4: Create `templates/setup.html`**

```html
<!doctype html>
<html>
<head><title>Debrief — Setup</title></head>
<body>
  <h1>Welcome to Debrief</h1>
  <p>Set a password to protect your local Debrief instance. You'll use this password to log in every time you launch the app.</p>
  {% if error %}<p style="color:red">{{ error }}</p>{% endif %}
  <form method="post">
    <input type="password" name="password" placeholder="Choose a password" required>
    <button type="submit">Set Password &amp; Continue</button>
  </form>
</body>
</html>
```

- [ ] **Step 5: Run tests to verify they pass, and confirm no regression**

Run: `pytest tests/test_setup.py -v`
Expected: PASS (3 tests)

Run: `pytest -v`
Expected: ALL existing tests still PASS — `FROZEN` defaults to `False` outside these specific frozen-mode tests, so every pre-existing test (which never sets `app_module.FROZEN = True`) exercises the unchanged env-var path.

- [ ] **Step 6: Commit**

```bash
git add app.py templates/setup.html tests/test_setup.py
git commit -m "feat: add first-run /setup screen and frozen-aware auth for packaged app"
```

---

### Task 3: Frozen-aware storage paths

**Files:**
- Modify: `app.py`

**Interfaces:**
- Consumes: `config.get_data_dir()` (Task 1), `app.FROZEN` (Task 2).
- Produces: no new interface — `db.DB_PATH` and `UPLOAD_DIR` are set to different values depending on `FROZEN`, everything downstream (routes, `pipeline.run_pipeline`) is unchanged.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_setup.py
def test_frozen_mode_uses_data_dir_for_db_and_uploads(tmp_path, monkeypatch):
    import importlib
    import app as app_module
    importlib.reload(app_module)

    app_module.FROZEN = True
    data_dir = str(tmp_path / 'DebriefData')
    monkeypatch.setattr(app_module.cfg, 'get_data_dir', lambda: data_dir)

    # Re-run the module-level path setup that normally runs at import time
    app_module.configure_storage_paths()

    import os
    assert app_module.UPLOAD_DIR.startswith(data_dir)
    import db
    assert db.DB_PATH.startswith(data_dir)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_setup.py::test_frozen_mode_uses_data_dir_for_db_and_uploads -v`
Expected: FAIL — `app.configure_storage_paths` doesn't exist.

- [ ] **Step 3: Modify `app.py`**

Find the existing module-level block that sets `UPLOAD_DIR` (added in the v1 plan's Task 7/8):

```python
UPLOAD_DIR = os.environ.get('DEBRIEF_UPLOAD_DIR', 'uploads')
UPLOAD_DIR = os.path.abspath(UPLOAD_DIR)
os.makedirs(UPLOAD_DIR, exist_ok=True)
```

Replace it with a function so tests can re-invoke the same logic after monkeypatching, and call that function once at module load:

```python
UPLOAD_DIR = None


def configure_storage_paths():
    global UPLOAD_DIR
    if FROZEN:
        data_dir = cfg.get_data_dir()
        db.DB_PATH = os.path.join(data_dir, 'debrief.db')
        UPLOAD_DIR = os.path.join(data_dir, 'uploads')
    else:
        UPLOAD_DIR = os.environ.get('DEBRIEF_UPLOAD_DIR', 'uploads')
    UPLOAD_DIR = os.path.abspath(UPLOAD_DIR)
    os.makedirs(UPLOAD_DIR, exist_ok=True)


configure_storage_paths()
```

Make sure this call happens AFTER `FROZEN` is defined and BEFORE `db.init_db()` runs (so a frozen run initializes the DB at the new path, not the default). Move `db.init_db()` to after `configure_storage_paths()` if it isn't already.

- [ ] **Step 4: Run tests to verify they pass, and confirm no regression**

Run: `pytest tests/test_setup.py -v`
Expected: PASS (4 tests)

Run: `pytest -v`
Expected: ALL tests still PASS — non-frozen tests never touch `configure_storage_paths`'s frozen branch.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_setup.py
git commit -m "feat: use %LOCALAPPDATA%\\Debrief for DB and uploads when running as a packaged exe"
```

---

### Task 4: PyInstaller build script and manual build verification

**Files:**
- Create: `debrief.spec`
- Modify: `requirements.txt` (add `pyinstaller` as a build-time dependency — document it's build-only, not runtime)
- Create: `BUILDING.md`

**Interfaces:** none — this is a build artifact, not application code.

- [ ] **Step 1: Add PyInstaller to `requirements.txt`**

```
Flask==3.0.3
pytest==8.3.2
faster-whisper==1.0.3
openai==1.40.0
anthropic==0.34.0
pyinstaller==6.10.0
```

- [ ] **Step 2: Create `debrief.spec`**

```python
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static')]
binaries = []
hiddenimports = []

for pkg in ('faster_whisper', 'ctranslate2', 'onnxruntime', 'tokenizers'):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='debrief',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

`console=True` is deliberate for v1 — a visible console window shows server logs/tracebacks, which matters for a single-user tool with no other error-reporting mechanism.

- [ ] **Step 3: Create `BUILDING.md`**

```markdown
# Building debrief.exe

```cmd
pip install -r requirements.txt
pyinstaller debrief.spec
```

The built executable is at `dist\debrief.exe`.

## Manual verification (required before shipping a build)

There is no automated test for the packaging step itself — PyInstaller
bundling of `faster-whisper`'s native dependencies (`ctranslate2`,
`onnxruntime`) is the highest-risk part and can only be confirmed by
actually running the built exe:

1. Copy `dist\debrief.exe` to a clean folder (not the source checkout) and
   double-click it.
2. Confirm the first-run `/setup` screen appears (not the source-mode
   env-var misconfiguration error).
3. Set a password, confirm it redirects to `/login` and logs in correctly.
4. Confirm `%LOCALAPPDATA%\Debrief\config.json`, `debrief.db`, and
   `uploads\` all get created there, not next to the exe.
5. Click Start Recording, record a few seconds of real audio, Stop & Save,
   and confirm a transcript and MEDDIC/BANT summary appear (local Whisper
   will download its model from Hugging Face on first use — this requires
   internet the first time only).
6. Close and relaunch the exe — confirm it goes straight to `/login` (not
   `/setup` again) and the earlier call still appears in history.

If step 5 fails with a missing-module error, PyInstaller likely needs an
additional `--collect-all` entry in `debrief.spec` for whatever `ctranslate2`
or `onnxruntime` submodule wasn't picked up.
```

- [ ] **Step 4: Build the exe and run the manual verification above**

Run: `pip install -r requirements.txt` then `pyinstaller debrief.spec`
Expected: `dist\debrief.exe` is produced with no build errors.

Perform all 6 manual verification steps from `BUILDING.md`. Fix any missing-import errors by adding the affected package to the `collect_all` loop in `debrief.spec` and rebuilding, repeating until all 6 steps pass.

- [ ] **Step 5: Commit**

```bash
git add debrief.spec requirements.txt BUILDING.md
git commit -m "build: add PyInstaller packaging for a portable debrief.exe"
```

(Do not commit `dist/` or `build/` — add both to `.gitignore` if not already covered by existing `__pycache__`/`*.pyc` entries.)

- [ ] **Step 6: Ensure build artifacts are gitignored**

Check `.gitignore` contains `dist/` and `build/`; if not, add them and commit:

```bash
# append to .gitignore if missing
echo "dist/" >> .gitignore
echo "build/" >> .gitignore
git add .gitignore
git commit -m "chore: gitignore PyInstaller build output"
```

---

### Task 5: Designmodo-inspired landing/download site

**Files:**
- Create: `site/index.html`
- Create: `site/css/style.css`

**Interfaces:** none — static content, no automated tests.

- [ ] **Step 1: Create `site/index.html`**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Debrief — Turn call notes into a structured summary</title>
  <link rel="stylesheet" href="css/style.css">
</head>
<body>
  <header class="site-header">
    <div class="container header-row">
      <span class="logo">Debrief</span>
      <a class="btn btn-small" href="https://github.com/HaydenVandercraats/debrief/releases/latest">Download →</a>
    </div>
  </header>

  <section class="hero">
    <div class="container">
      <h1>Stop writing call notes from memory.</h1>
      <p class="subhead">Debrief records both sides of your sales call, transcribes it locally, and turns it into a structured MEDDIC/BANT summary — automatically.</p>
      <a class="btn btn-primary" href="https://github.com/HaydenVandercraats/debrief/releases/latest">Download for Windows →</a>
      <p class="hero-note">Free. Runs on your machine. Your call audio never leaves your computer.</p>
    </div>
  </section>

  <section class="features">
    <div class="container feature-grid">
      <div class="feature-card">
        <h3>Records both sides</h3>
        <p>Captures your mic and the call's system audio together, so you get the full conversation, not just your half.</p>
      </div>
      <div class="feature-card">
        <h3>Transcribes locally, for free</h3>
        <p>Runs Whisper on your own machine — no per-call API cost, no audio sent anywhere.</p>
      </div>
      <div class="feature-card">
        <h3>Auto-tags MEDDIC/BANT</h3>
        <p>Surfaces budget, timeline, pain, and decision-maker signals from the transcript automatically.</p>
      </div>
      <div class="feature-card">
        <h3>Your data stays yours</h3>
        <p>No account, no cloud storage. Everything lives in a local file on your own machine.</p>
      </div>
    </div>
  </section>

  <section class="how-it-works">
    <div class="container">
      <h2>How it works</h2>
      <ol class="steps">
        <li>Download and run <code>debrief.exe</code> — no Python install needed.</li>
        <li>Set a password on first launch.</li>
        <li>Join your call, click Start Recording, share your tab/screen with audio.</li>
        <li>Click Stop &amp; Save — get a transcript and MEDDIC/BANT summary.</li>
      </ol>
    </div>
  </section>

  <footer class="site-footer">
    <div class="container">
      <p><a href="https://github.com/HaydenVandercraats/debrief">Source on GitHub</a></p>
      <p class="limitations">Windows only for now. First transcription requires a one-time internet connection to download the local speech-to-text model.</p>
    </div>
  </footer>
</body>
</html>
```

- [ ] **Step 2: Create `site/css/style.css`**

```css
:root {
  --ink: #16181d;
  --muted: #5b6270;
  --line: #e6e8ec;
  --bg: #ffffff;
  --accent: #16181d;
  --card-bg: #fafafa;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  color: var(--ink);
  background: var(--bg);
  line-height: 1.5;
}

.container {
  max-width: 1080px;
  margin: 0 auto;
  padding: 0 24px;
}

.site-header {
  border-bottom: 1px solid var(--line);
  padding: 20px 0;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  font-weight: 700;
  font-size: 20px;
  letter-spacing: -0.02em;
}

.btn {
  display: inline-block;
  text-decoration: none;
  font-weight: 600;
  border-radius: 8px;
  padding: 12px 22px;
  background: var(--accent);
  color: #fff;
  transition: opacity 0.15s ease;
}

.btn:hover { opacity: 0.85; }

.btn-small { padding: 8px 16px; font-size: 14px; }

.hero {
  padding: 96px 0 72px;
  text-align: center;
}

.hero h1 {
  font-size: 48px;
  line-height: 1.1;
  letter-spacing: -0.02em;
  margin: 0 0 20px;
  max-width: 760px;
  margin-left: auto;
  margin-right: auto;
}

.subhead {
  font-size: 19px;
  color: var(--muted);
  max-width: 620px;
  margin: 0 auto 32px;
}

.btn-primary { font-size: 17px; padding: 16px 32px; }

.hero-note {
  margin-top: 16px;
  font-size: 14px;
  color: var(--muted);
}

.features { padding: 64px 0; background: var(--card-bg); }

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 24px;
}

.feature-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 28px;
  box-shadow: 0 1px 2px rgba(16, 18, 21, 0.04);
}

.feature-card h3 { margin: 0 0 10px; font-size: 18px; }
.feature-card p { margin: 0; color: var(--muted); font-size: 15px; }

.how-it-works { padding: 72px 0; }
.how-it-works h2 { font-size: 30px; margin-bottom: 24px; text-align: center; }

.steps {
  max-width: 560px;
  margin: 0 auto;
  padding-left: 20px;
  color: var(--muted);
  font-size: 16px;
}

.steps li { margin-bottom: 12px; }
.steps code { background: var(--card-bg); padding: 2px 6px; border-radius: 4px; }

.site-footer {
  border-top: 1px solid var(--line);
  padding: 32px 0;
  text-align: center;
  color: var(--muted);
  font-size: 14px;
}

.site-footer a { color: var(--ink); }
.limitations { margin-top: 8px; }

@media (max-width: 640px) {
  .hero h1 { font-size: 34px; }
  .hero { padding: 64px 0 48px; }
}
```

- [ ] **Step 3: Manual verification**

Open `site/index.html` directly in a browser (`file://` path is fine for this check). Confirm: hero renders with headline + download button, 4 feature cards lay out in a responsive grid, "how it works" list renders, footer links are present. Resize the window narrow and confirm the feature grid reflows to fewer columns and the hero heading shrinks (per the `@media` rule).

- [ ] **Step 4: Commit**

```bash
git add site/index.html site/css/style.css
git commit -m "feat: add Designmodo-inspired landing/download page"
```

---

### Task 6: README updates for packaging, GitHub, and Render deploy

**Files:**
- Modify: `README.md`

**Interfaces:** none — documentation only.

- [ ] **Step 1: Add a "Packaged App" section to `README.md`**

Add this section after the existing "Local Setup" section:

```markdown
## Packaged App (no Python required)

A portable Windows executable is built via PyInstaller — see `BUILDING.md`
for build instructions and the required manual verification steps before
shipping a build.

On first launch, `debrief.exe` shows a one-time setup screen to choose a
password (instead of the `DEBRIEF_PASSWORD` env var used in the source/dev
workflow above). The database and uploaded audio are stored in
`%LOCALAPPDATA%\Debrief\` rather than the current working directory.

## Landing Page & Distribution

- The marketing/download site lives in `site/` (plain HTML/CSS, no build
  step) and deploys to Render as a static site.
- To publish a new build: build `debrief.exe` (see `BUILDING.md`), push this
  repo to GitHub, cut a GitHub Release, and attach the exe as a release
  asset — the site's Download button links to
  `https://github.com/HaydenVandercraats/debrief/releases/latest`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document packaged app, config-based auth, and landing site"
```
