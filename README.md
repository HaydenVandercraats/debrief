# Debrief

Local-only call-notes tool. Records both sides of a sales call (your mic +
system audio from Zoom/Meet/Teams), transcribes it, and extracts a
structured MEDDIC/BANT summary.

Phase 2 of the [10-tool BD/GTM roadmap](../portfolio-site), following Primer.

## Local Setup

```cmd
pip install -r requirements.txt
set DEBRIEF_PASSWORD=your-password-here
set SECRET_KEY=any-random-string
set DEBRIEF_TIER=free
python app.py
```

Visit `http://localhost:5000`.

**Both `DEBRIEF_PASSWORD` and `SECRET_KEY` must be set** — there is no safe
default for either. If `DEBRIEF_PASSWORD` is unset, login is rejected
outright. If `SECRET_KEY` is unset, a fresh random key is generated each
process start (sessions won't survive a restart).

### Tiers

- `DEBRIEF_TIER=free` (default): transcription via local Whisper
  (`faster-whisper`, runs on your machine, no API cost), summary via
  rule-based keyword tagging.
- `DEBRIEF_TIER=pro`: transcription via OpenAI's Whisper API, summary via a
  Claude API extraction call. Requires `OPENAI_API_KEY` and
  `ANTHROPIC_API_KEY` — the app refuses to start without them when
  `DEBRIEF_TIER=pro`.

### Recording

Click "Start Recording", then share your screen or the call's browser tab
with "Share audio" checked (this captures system audio, i.e. the call
itself), and allow microphone access when prompted. Click "Stop & Save" when
the call ends. Processing runs synchronously — Free-tier local Whisper can
take a few minutes for a longer call.

Audio is discarded immediately after transcription by default. Check "Keep
audio recording" before starting to retain the file (enables retry on
failure and re-listening).

## Packaged App (no Python required)

A portable Windows executable is built via PyInstaller — see `BUILDING.md`
for build instructions and the required manual verification steps before
shipping a build.

On first launch, `debrief.exe` shows a one-time setup screen to choose a
password (instead of the `DEBRIEF_PASSWORD` env var used in the source/dev
workflow above). The database and uploaded audio are stored in
`%LOCALAPPDATA%\Debrief\` rather than the current working directory.

Once running, open `http://localhost:5000` in your browser (the console
window also prints this URL on startup).

This release is Windows-only — there is no macOS/Linux build.

The first time you actually transcribe a call, `debrief.exe` downloads the
local Whisper speech-to-text model (~150MB). This happens once and requires
an internet connection; the app will appear to hang during this download,
so expect the first recording to take noticeably longer than subsequent
ones.

`debrief.exe` is unsigned, so Windows SmartScreen will show an "Unknown
publisher" warning on first run — click "More info" → "Run anyway" to
continue.

There is no installer or uninstaller in this version, by design. To remove
the app, delete `debrief.exe` and the `%LOCALAPPDATA%\Debrief\` folder.

## Landing Page & Distribution

- The marketing/download site lives in `site/` (plain HTML/CSS, no build
  step) and deploys to Render as a static site.
- To publish a new build: build `debrief.exe` (see `BUILDING.md`), push this
  repo to GitHub, cut a GitHub Release, and attach the exe as a release
  asset — the site's Download button links to
  `https://github.com/HaydenVandercraats/debrief/releases/latest`.

## Running Tests

```bash
pytest -v
```

## Known Limitations (v1)

- Local-only — not deployed anywhere. Must run on the machine you're taking
  the call from.
- Free-tier transcription (local Whisper) needs real local compute; a
  30-minute call may take a few minutes to process.
- No live/real-time transcript during the call — processing happens after
  you click "Stop & Save".
- Free/Pro tier is a config toggle (`DEBRIEF_TIER`), not a real paywall.
