import os
import secrets
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, abort

import db

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


if __name__ == '__main__':
    app.run(debug=True)
