# Building debrief.exe

```cmd
pip install -r requirements.txt
pyinstaller debrief.spec
```

The built executable is at `dist\debrief.exe`.

## Architecture

`debrief.exe` is a **windowed app, no console** (`console=False` in
`debrief.spec`). On launch it starts the Flask server on a background
thread, waits for it to accept connections, then opens a native window via
`pywebview` (using Windows' built-in WebView2 engine) pointed at
`http://127.0.0.1:<port>`. There's no separate browser tab and no visible
terminal — just one app window, same as any other desktop app.

Because it's windowed, `sys.stdout`/`sys.stderr` are `None` at runtime, not
just a closed stream — `app.py` detects this (`FROZEN` + `sys.stdout is
None`) and redirects both to a null sink so any library code that
unconditionally writes to them (Werkzeug's own startup banner, for example)
doesn't crash with `AttributeError: 'NoneType' object has no attribute
...`. This bit us once already — if a future change reintroduces a bare
`print()`/`sys.stdout.write()` call anywhere in the `FROZEN` path, this is
why it can crash a windowed build even though it works fine from source.

## Manual verification (required before shipping a build)

There is no automated test for the packaging step itself — PyInstaller
bundling of `faster-whisper`'s native dependencies (`ctranslate2`,
`onnxruntime`) AND `pywebview`'s Windows backend (`clr_loader`, `pythonnet`,
WebView2) is the highest-risk part and can only be confirmed by actually
running the built exe. Since there's no console to watch, verify via HTTP
instead of visual inspection when scripting this (see git history for the
`curl`-based check used during development) — or just watch for the actual
window to open when running it interactively:

1. Copy `dist\debrief.exe` to a clean folder (not the source checkout) and
   double-click it. Expect a several-second delay (self-extracting a
   ~120MB onefile bundle) before a window appears — this is normal, not a
   hang.
2. Confirm the app window opens and shows the first-run `/setup` screen
   (not a blank window, not a crash, not the source-mode env-var
   misconfiguration error).
3. Set a password, confirm it moves to `/login` and logs in correctly.
4. Confirm `%LOCALAPPDATA%\Debrief\config.json`, `debrief.db`, and
   `uploads\` all get created there, not next to the exe.
5. Click Start Recording, record a few seconds of real audio, Stop & Save,
   and confirm a transcript and MEDDIC/BANT summary appear (local Whisper
   will download its model from Hugging Face on first use — this requires
   internet the first time only).
6. Close and relaunch the exe — confirm it goes straight to `/login` (not
   `/setup` again) and the earlier call still appears in history.

If step 5 fails with a missing-module error, PyInstaller likely needs an
additional entry in `debrief.spec`'s `collect_all` loop for whatever
`ctranslate2`/`onnxruntime` submodule wasn't picked up. If the window never
appears at all (process alive but nothing listening, or the process exits
immediately), check `clr_loader`/`pythonnet`/`webview` are all present in
that same loop — pywebview's WebView2 backend needs all three bundled
explicitly; PyInstaller's automatic dependency analysis doesn't reliably
catch them on its own.

If port 5000 is already in use on your test machine, set `DEBRIEF_PORT`
before launching to avoid a collision with something else.
