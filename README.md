# Clipping Fingerprint

A forkable **Hermes Agent distribution + SupoClip source snapshot + local FFmpeg/Remotion render toolkit**. It captures the editorial rules, style presets, caption behaviours, framing/cut controls and QA procedures developed for this clipping agent.

**This ships the workflow—not a model clone.** Identical inputs, approved timelines, fonts and tool versions can reproduce a specified edit. Different LLMs, ASR providers, browser/FFmpeg builds and editorial decisions can produce different outputs. No claim of universal automatic highlight selection or guaranteed virality is made.

## What's included

- **Creator / talking-stream format:** persistent meme/satire hero; one spoken word at a time with pop-in; selective emphasis, reviewed crops and motivated shot/zoom choices. Fast static-glyph atlas + transparent caption-band renderer avoids capturing Chrome on every output frame.
- **Podcast / interview format:** separate locked Poppins ExtraBold look, sequential grouped captions, selective highlights, optional inline red strikes, complete question/answer structure, deliberate framing and reaction-hold rules. Optional supplied effects require your own licensed audio and source-specific cues.
- **Reaction / split-screen building blocks:** source-preserving layouts, supporting footage, labels/callouts/counters in the configurable creator graphics engine. These are editable components, not verified automatic gameplay-event or speaker detection.
- **Editorial judgement rules:** immediate hooks, real curiosity/payoff, fast smooth pacing, emotional relevance, share motivations, truthful playful debate, natural replay seams and audience/campaign overrides.
- **Source review and QA:** coarse-to-fine audio/visual review cues, timeline/caption validation, full decode, ffprobe, contact sheets, all-frame picture-regression checks and explicit pending manual review.
- **Hermes integration:** authored SOUL, skills, native distribution manifest, safe isolated installer, local MCP launcher, local progress records and optional verified Telegram delivery with your own bot/chat.
- **Upstream SupoClip application:** backend, frontend, MCP client, docs and preserved dependency lockfiles/license. The bespoke local graphics workflow is separate from the automatic service/web editor.

## Quick start — native renderer

Requires Python 3.11+, FFmpeg/ffprobe with libx264, Node compatible with the pinned pnpm version, pnpm 11.24.0, and installed Chrome/Chromium. No model, paid provider or source-video download is needed for the smoke test.

```sh
git clone https://github.com/kofiowusuai-lab/clipping-fingerprint.git
cd clipping-fingerprint
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-fingerprint.txt
pnpm --dir remotion install --frozen-lockfile
.venv/bin/python scripts/fingerprint_smoke.py smoke --output-dir outputs/smoke-01
```

The smoke generates an explicitly **synthetic** video/tone, renders both creator and podcast MP4s, probes and decodes them, checks graphics/picture regression and emits `smoke-report.json`. It does **not** certify real editorial quality, lip sync, captions from speech, rights or delivery. Output directories must be fresh. See [verification](docs/VERIFICATION.md) for what was actually exercised on this release.

## Container

```sh
docker build -f Dockerfile.fingerprint -t clipping-fingerprint:local .
docker run --rm --network none --shm-size 1g clipping-fingerprint:local
```

The rendering image intentionally does not include Hermes credentials, Whisper/torch/models, the web stack, bot accounts or source clips. Dependency installation requires network at build time; synthetic rendering can run without network. For persisted outputs and actual jobs, see [setup](docs/FINGERPRINT-SETUP.md) and `compose.fingerprint.yml`. The image supports `creator`, `creator-engine`, `creator-batch`, `podcast`, `podcast-captions`, `creator-graphics`, `creator-atlas`, `caption-band` and `remotion` commands through its entrypoint. Input/job/output paths in container jobs must use container paths such as `/inputs` and `/outputs`.

## Connect your Hermes

Install Hermes using its [official docs](https://hermes-agent.nousresearch.com/docs/). Bring your own model/provider authorization.

**Safe checkout-based install** (recommended; refuses an existing destination):

```sh
.venv/bin/python -m pip install python-dotenv==1.2.2 -e ./mcp
.venv/bin/python scripts/install_fingerprint.py --profile-home "$HOME/.hermes/profiles/myclipper"
HERMES_HOME="$HOME/.hermes/profiles/myclipper" hermes setup
HERMES_HOME="$HOME/.hermes/profiles/myclipper" hermes chat
```

Alternatively, the root is a native distribution:

```sh
hermes profile install github.com/kofiowusuai-lab/clipping-fingerprint --name myclipper
```

That installs the **agent rules**, not Python/npm dependencies or a running media backend. Keep a checkout for the executable toolkit; configure its working directory and MCP connection as documented in [setup](docs/FINGERPRINT-SETUP.md). Neither method copies this author's credentials, memories, bot routing or session history. Private-repo consumers need GitHub access; a fork owner should replace the clone URL above with their fork.

## Supported versus experimental

- Creator/talking-stream and podcast/interview are the two established editable style families. Fresh technical smoke evidence is recorded separately from historical real-source usage.
- Creator timing currently supports 24/30 fps at the validated graphics layer; the synthetic release smoke is 30 fps. Native frame-rate normalization must be explicit.
- Multi-face speaker selection, natural reaction selection, gaming semantics (kills/wins/HUD) and general sports-event understanding are **not** established automatic capabilities. Human source review remains required.
- MP4/MOV/WebM/MKV source support depends on FFmpeg codecs and the selected renderer's validator. Final delivery is H.264/AAC MP4. This is not a tested exotic-codec/HDR/VFR matrix.
- Older episode-named scripts are preserved as **historical recipes**, some superseded/rejected, not default production entrypoints. Their original source media, outputs and SFX are intentionally absent. Do not run every script as a test: some upstream maintenance tools contact cloud/production services.

## Before publishing a real clip

Read `SOUL.md`, `AGENTS.md`, the matching skill, and the editorial checklist. Review real source audio **and** video, use an approved clip plan, inspect actual rendered openings/closings/cuts/captions/framing, check source-timeline audio-picture alignment, and deliver only after the checks. Include matching post copy/hashtags in a fenced copyable block. Do not publish or submit a campaign without permission.

Use `scripts/trim_reviewed_pauses.py` to shorten explicitly reviewed thinking pauses in an existing export while cutting picture/audio/burned-in captions together; it does not classify silence automatically. Never speed speech up just to remove dead air.

## Security and licensing

- No `.env` secrets, auth stores, chat histories, memories, cached source videos, Whisper weights or original Telegram routing are committed.
- `scripts/audit_fingerprint.py` scans the exact Git publish set. It can compare against locally supplied secret files without printing values. It is a useful gate, not a comprehensive security audit.
- SupoClip and added workflow code retain **AGPL-3.0-or-later**; upstream credit and source provenance are preserved. Remotion, fonts, models and any supplied media have separate terms. Read [asset/license notes](docs/ASSETS-AND-LICENSES.md).
- Do not redistribute source footage or supplied sounds merely because the tooling can read them. No outside music/SFX or license purchase happens automatically.

Further reading: [setup](docs/FINGERPRINT-SETUP.md), [reproducibility](docs/REPRODUCIBILITY.md), [release verification](docs/VERIFICATION.md), [snapshot audit](docs/FINGERPRINT-AUDIT.md), [editorial principles](skills/supoclip-operations/references/short-form-editorial-principles.md), and [original SupoClip docs](docs/README.md).
