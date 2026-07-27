# Debrief — Design Spec

**Date:** 2026-07-27
**Status:** Approved (v1 scope)

## Purpose

Debrief is a local-only desktop web app that records both sides of a live sales
call (your mic + the prospect's audio from Zoom/Meet/Teams), transcribes it,
and extracts a structured MEDDIC/BANT summary. It's Phase 2 of Hayden's
[10-tool BD/GTM roadmap](../../../..), following the same build pipeline as
Primer (Phase 1).

The problem it solves: call notes written from memory after the fact lose
detail and rarely map cleanly to a qualification framework. Debrief captures
the call itself and produces the structured summary directly from what was
actually said.

## Architecture

- **Stack:** Flask + SQLite, same as Primer.
- **Auth:** single-user password gate. `DEBRIEF_PASSWORD` and `SECRET_KEY`
  must be set as real environment variables — no safe defaults. If
  `DEBRIEF_PASSWORD` is unset, login is rejected outright ("Server
  misconfigured"), matching Primer's hardened pattern.
- **Deployment:** local-only. Runs as `python app.py` on Hayden's own machine.
  Not deployed to Render like Primer — audio capture only works on the
  machine placing/joining the call, and Free-tier transcription (local
  Whisper) needs to run on real hardware, not a Render free-tier container.
  Built with the same Flask/SQLite structure regardless, so a server-side
  deployment remains possible later if the transcription step moves off-box
  (e.g. Pro-only hosted mode).
- **Tiering:** `DEBRIEF_TIER` env var (`free` or `pro`) selects the
  processing path. This is a config toggle only in v1 — no billing/paywall.
  It is architected as a real product tier boundary (clean separation between
  tier-specific code paths) so a future Stripe paywall (as in Vanish) can
  slot in later without a rewrite.

## Client-side audio capture

1. User clicks **Start Recording**.
2. Browser prompts for screen/tab share via `getDisplayMedia({ audio: true })`
   — user selects "Entire Screen" (or the call's browser tab) with
   "Share audio" checked, capturing system audio (the call, both sides as
   played back).
3. Browser also requests the microphone via `getUserMedia({ audio: true })`.
4. Both `MediaStream`s are mixed into one via the Web Audio API
   (`AudioContext` + `MediaStreamAudioSourceNode` per stream →
   `MediaStreamAudioDestinationNode`).
5. The mixed stream is recorded via `MediaRecorder` into a single webm/opus
   blob, held client-side until the user clicks **Stop & Save**.
6. On **Stop & Save**, the blob uploads to the Flask backend, which creates a
   `calls` row with `status=transcribing`.

This capture flow is identical for both tiers — Free and Pro only diverge in
which engine processes the resulting blob.

## Backend processing by tier

**Free tier:**
- Transcription: local Whisper (`faster-whisper`), run as a subprocess/library
  call against the uploaded blob. No API cost, no network dependency.
- Summarization: rule-based keyword/pattern tagging (same style as Primer's
  `playbook.py`) scans the transcript and assigns matching sentences to each
  MEDDIC/BANT field. Fields with no match are left empty — never fabricated.

**Pro tier:**
- Transcription: OpenAI Whisper API (cloud), higher accuracy than local
  Whisper, ~$0.006/min.
- Summarization: single bounded Claude API call with a MEDDIC/BANT extraction
  prompt, returning structured JSON. Synthesizes 1-2 sentence extractions per
  field rather than raw sentence matches.
- Requires `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` set. Missing keys fail
  fast at startup with a clear misconfiguration error — Pro tier never
  silently falls back to Free.

## Audio retention

Default: the uploaded audio blob is deleted immediately after transcription
succeeds — only the transcript and structured summary persist. This is opt-out
via a `KEEP_AUDIO=true` env var, or a per-recording "keep audio" checkbox in
the UI, which retains the file (`audio_path` populated, `audio_kept=1`) for
later re-listening or re-transcription. Reduces default privacy/storage
exposure from recording another party's voice.

## Data model (SQLite)

`calls` table:

| Column | Type | Notes |
|---|---|---|
| id | integer PK | |
| created_at | datetime | |
| company | text, nullable | freeform |
| contact_name | text, nullable | freeform |
| tier_used | text | `free` or `pro` |
| audio_kept | boolean | default false |
| audio_path | text, nullable | set only if `audio_kept` |
| transcript | text, nullable | |
| summary_json | text (JSON), nullable | see below |
| status | text | `recording` / `transcribing` / `summarizing` / `done` / `failed` |
| error_message | text, nullable | set when `status=failed` |

`summary_json` shape (both tiers, same keys):

```json
{
  "metrics": "",
  "economic_buyer": "",
  "decision_criteria": "",
  "decision_process": "",
  "identify_pain": "",
  "champion": "",
  "budget": "",
  "authority": "",
  "need": "",
  "timeline": ""
}
```

Free tier: each value is the matched excerpt sentence(s), or `""` if no match.
Pro tier: each value is a synthesized 1-2 sentence extraction, or `""` if the
signal wasn't present in the call.

## Error handling

- **Permission denied** (screen-share or mic): show an in-page error, do not
  create a `calls` row, no partial recording saved.
- **Empty/near-silent capture**: before upload, check the blob isn't
  effectively silent (e.g. selected wrong share source); warn instead of
  spending a transcription pass on nothing.
- **Transcription failure** (local Whisper crash, Pro API error/timeout): row
  saved with `status=failed` and `error_message`, visible in the call history
  so nothing silently disappears. A retry action re-runs transcription from
  the retained audio (if `audio_kept`) or prompts re-upload if it was
  discarded.
- **Pro tier misconfiguration** (missing API keys): fail fast at startup,
  never silently degrade to Free-tier behavior.

## Testing

- Backend (tier routing, rule-based tagging, Claude extraction prompt +
  response parsing, DB layer, error paths): pytest, TDD, mirrors Primer's
  test suite structure.
- Client-side audio capture/mixing: not meaningfully unit-testable (depends
  on real OS-level screen-share/mic permissions and hardware). Verified via
  manual browser testing per the feature-test skill pattern instead.

## Known deviations from the Primer pattern

- **No live public URL.** Since this stays local-only, the portfolio-site
  case study will need a demo recording/GIF instead of a live link. This is
  an accepted deviation, not a gap to close later.
- **Free tier is not $0-infrastructure like Primer's v1.** Local Whisper
  requires real local compute (a 30-min call may take a few minutes to
  transcribe on CPU) — still no per-call API cost, but not instant either.

## Future work (explicit non-goals for v1)

- Stripe-backed real paywall for Free/Pro (currently env-var toggle only).
- Server-side deployment option once/if a hosted transcription path exists.
- Export (PDF/CRM push) of the structured summary.
- Live/real-time transcript display during the call (deferred — v1 is
  after-the-call only, per design decision).
