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
