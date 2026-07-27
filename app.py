import os
import secrets
import uuid
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, abort

import db
import pipeline

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

DEBRIEF_TIER = os.environ.get('DEBRIEF_TIER', 'free')
if DEBRIEF_TIER not in ('free', 'pro'):
    raise RuntimeError(f"DEBRIEF_TIER must be 'free' or 'pro', got {DEBRIEF_TIER!r}")
if DEBRIEF_TIER == 'pro':
    if not os.environ.get('OPENAI_API_KEY'):
        raise RuntimeError('DEBRIEF_TIER=pro requires OPENAI_API_KEY to be set.')
    if not os.environ.get('ANTHROPIC_API_KEY'):
        raise RuntimeError('DEBRIEF_TIER=pro requires ANTHROPIC_API_KEY to be set.')

db.init_db()

UPLOAD_DIR = os.environ.get('DEBRIEF_UPLOAD_DIR', 'uploads')
UPLOAD_DIR = os.path.abspath(UPLOAD_DIR)
os.makedirs(UPLOAD_DIR, exist_ok=True)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        expected_password = os.environ.get('DEBRIEF_PASSWORD')
        if expected_password is None:
            error = 'Server misconfigured: DEBRIEF_PASSWORD is not set.'
            return render_template('login.html', error=error)
        if request.form.get('password') == expected_password:
            session['logged_in'] = True
            return redirect(url_for('index'))
        error = 'Incorrect password.'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    calls = db.list_calls()
    return render_template('index.html', calls=calls, tier=DEBRIEF_TIER)


@app.route('/calls', methods=['POST'])
@login_required
def upload_call():
    company = request.form.get('company', '').strip() or None
    contact_name = request.form.get('contact_name', '').strip() or None
    keep_audio = request.form.get('keep_audio') == 'on'
    audio_file = request.files['audio']

    filename = f'{uuid.uuid4().hex}.webm'
    audio_path = os.path.join(UPLOAD_DIR, filename)
    audio_file.save(audio_path)

    call_id = db.create_call(
        company=company,
        contact_name=contact_name,
        tier_used=DEBRIEF_TIER,
        audio_kept=keep_audio,
        audio_path=audio_path if keep_audio else None,
    )

    pipeline.run_pipeline(call_id, audio_path, DEBRIEF_TIER, keep_audio)

    return redirect(url_for('call_detail', call_id=call_id))


@app.route('/calls/<int:call_id>')
@login_required
def call_detail(call_id):
    record = db.get_call(call_id)
    if record is None:
        abort(404)
    return render_template('call_detail.html', call=record)


@app.route('/calls/<int:call_id>/retry', methods=['POST'])
@login_required
def retry_call(call_id):
    record = db.get_call(call_id)
    if record is None:
        abort(404)
    if not record['audio_kept'] or not record['audio_path'] or not os.path.exists(record['audio_path']):
        return 'Audio was not retained for this call — please re-record it.', 400

    pipeline.run_pipeline(call_id, record['audio_path'], record['tier_used'], keep_audio=True)
    return redirect(url_for('call_detail', call_id=call_id))


if __name__ == '__main__':
    app.run(debug=True)
