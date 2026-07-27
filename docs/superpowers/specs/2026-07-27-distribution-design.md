# Debrief Distribution — Design Spec

**Date:** 2026-07-27
**Status:** Approved (proceeding under standing instruction to run continuously with recommendations, no further approval gates)

## Purpose

Let someone download Debrief as a single portable Windows `.exe` (no Python
install required) from a public landing/download page styled after
Designmodo: bold flat hero, product-card-style feature grid, high
whitespace, arrow-style CTA buttons, no gradients.

This has two coupled but separable parts: (1) packaging changes to the app
itself so it can run as a double-clicked executable with no terminal/env-var
setup, and (2) a static marketing site that explains the tool and links to
the download.

## Part 1 — Packaging changes to the app

### First-run setup screen

Today, `app.py` requires `DEBRIEF_PASSWORD` and `SECRET_KEY` as environment
variables, checked at import time. That doesn't fit a double-clicked `.exe`
with no terminal. Packaging replaces this with a local config file:

- **Config location:** `%LOCALAPPDATA%\Debrief\config.json`, created on
  first run. Contains `{"password_hash": "<werkzeug generate_password_hash
  output>", "secret_key": "<random 64-char hex, secrets.token_hex(32)>"}`.
- **On launch, if the config file doesn't exist:** the only reachable route
  is `GET/POST /setup` — a single password field, no confirm field (single-user
  local tool, not a public signup form). Submitting writes the config file
  (creating `%LOCALAPPDATA%\Debrief\` if needed) and redirects to `/login`.
  Every other route redirects to `/setup` until the config exists.
- **On launch, if the config file exists:** behaves exactly like today's
  `/login` flow, except the expected password hash and `app.secret_key` are
  read from the config file instead of `os.environ`.
- **Corrupted/unreadable config file:** treated as "no config" — falls back
  to `/setup` rather than crashing. A user should never be crash-looped out
  of their own tool by a bad local file.
- **Dev workflow unaffected:** running via `python app.py` (not the frozen
  exe) keeps today's env-var-based behavior for `DEBRIEF_PASSWORD` /
  `SECRET_KEY` — this is a packaging addition, not a replacement of the
  existing local-dev path. Detection: `sys.frozen` (set by PyInstaller) picks
  the config-file path; its absence keeps the current env-var path.
- **Storage paths when frozen:** `db.DB_PATH` and the upload directory
  (`DEBRIEF_UPLOAD_DIR`) default into `%LOCALAPPDATA%\Debrief\` as well when
  `sys.frozen` is true, so a double-clicked exe launched from e.g. Downloads
  doesn't scatter `debrief.db`/`uploads/` into whatever folder it happened to
  be run from. Non-frozen (dev) behavior is unchanged (relative to cwd).
- **Pro tier stays env-var/advanced-only** for v1 — not part of the
  first-run flow. `DEBRIEF_TIER=pro` plus `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`
  remain environment variables for anyone who wants to set them manually;
  documented separately (README + site), not surfaced in the setup screen.

### PyInstaller bundling

- A build script/spec file (`build_exe.py` or `debrief.spec`) packages
  `app.py`, `templates/`, `static/`, and dependencies into one
  `debrief.exe` via PyInstaller, one-file mode.
- `faster-whisper`'s native dependencies (`ctranslate2`, `onnxruntime`) need
  explicit PyInstaller `--collect-all`/hidden-import handling — this is the
  highest-risk technical step and is verified by actually running the built
  exe, not by unit tests.
- The Whisper model weights are **not** bundled into the exe (keeps it a
  reasonable download size). First real transcription still downloads the
  ~150MB base model from Hugging Face on first use — same as today's dev
  behavior, just called out clearly on the landing page and in the README.
- Output: a single portable `debrief.exe`. No installer wizard, no Start
  Menu entry, no uninstaller — double-click to run, matching a personal
  single-user tool rather than a polished commercial install experience.

## Part 2 — Landing/download site

- New static site (plain HTML/CSS/vanilla JS, no build step, no framework)
  living in a `site/` subfolder of the `debrief` repo.
- **Sections:**
  - Hero: headline, one-line pitch, prominent "Download for Windows" button.
  - Feature grid (3-4 cards, Designmodo-style): record both sides of a call,
    transcribe locally for free (no per-call API cost), automatic MEDDIC/BANT
    tagging, "your data never leaves your machine" (privacy angle, since
    it's local-only).
  - Short "how it works" strip (download → run → join your call → get a
    structured summary).
  - Footer: link to the GitHub repo, known-limitations note (Windows only,
    first-run model download needs internet).
- **Visual direction (from Designmodo):** flat design, no gradients, generous
  whitespace, sans-serif type with clear size/weight hierarchy, card-based
  feature sections with subtle shadows, arrow-suffixed CTA buttons ("Download
  →"), high-contrast buttons against a white/near-white background.
- **Download button target:** a GitHub Release asset (the built
  `debrief.exe`) on the `debrief` repo. Requires pushing `debrief` to GitHub
  for the first time and cutting a release with the exe attached.
- **Deployment:** Render static site, connected to the GitHub repo (same
  account/pattern already used for Primer), serving the `site/` subfolder.

## Testing

- `tests/test_setup.py` (new): covers the `/setup` route — config file
  creation, password hashing, redirect behavior, corrupted-config fallback.
- `tests/test_auth.py` (updated): today's tests set `DEBRIEF_PASSWORD` via
  env var directly; since the frozen-app path now also supports a config
  file, these tests are updated to cover both mechanisms — env-var path
  (dev/test, unchanged behavior) and config-file path (new).
- Packaging itself is not unit-testable — verified by building `debrief.exe`
  and manually running it: confirm the setup screen appears on first launch,
  confirm login and the recording flow still work end-to-end afterward. Same
  manual-verification precedent as the v1 plan's Task 9 (browser recording
  flow).
- The static site has no automated tests — verified by opening it in a
  browser and clicking through, same as any static marketing page.

## Known limitations (documented on the site and in README)

- Windows only for v1 (matches the actual usage environment).
- First real transcription still requires internet once, to fetch the
  Whisper model — the exe itself doesn't need internet to run, but
  transcription won't produce output until that download completes.
- Still fundamentally a personal, local-only, single-user tool. Packaging
  removes "needs Python installed" as a barrier; it does not turn this into
  a hosted, multi-user product.
- No installer wizard/uninstaller (explicit v1 scope choice, not an
  oversight) — deleting `debrief.exe` and `%LOCALAPPDATA%\Debrief\` is the
  full removal process.

## Future work (explicit non-goals for this pass)

- macOS/Linux packaging.
- Bundling the Whisper model weights for a fully offline first run.
- A proper installer (Inno Setup) with Start Menu integration and uninstall
  entry.
- Surfacing Pro-tier configuration in the setup screen rather than
  env-vars-only.
