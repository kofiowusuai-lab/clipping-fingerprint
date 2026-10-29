# Installing and operating the fingerprint

## 1. Renderer environment

Clone this repository (or your fork), install the pinned rendering requirements in a fresh virtualenv and run `pnpm --dir remotion install --frozen-lockfile`. Do not copy another machine's `.venv` or `node_modules`. Install FFmpeg/ffprobe and Chrome/Chromium through your OS/package manager. The renderer checks common browser locations; set `REMOTION_BROWSER_EXECUTABLE` to an existing browser when necessary. Browser capture is serialized.

`requirements-fingerprint.txt` deliberately excludes torch, Whisper weights and the full backend. The local rendering path consumes **already reviewed words and edit plans**. It does not invent captions if transcription is unavailable. For new-source ASR, use existing YouTube JSON3 captions where available and independently verify selected speech, or explicitly provision a trusted local Whisper checkpoint. Full backend requirements are separate in `backend/uv.lock`.

Run the synthetic smoke in README first. Native macOS/Linux are the intended hosts; use the Linux container or WSL for Windows. Optional Telegram delivery uses fcntl and curl and is not a native Windows port.

## 2. New isolated Hermes profile

Install Hermes from the official docs, then from this checkout:

```sh
.venv/bin/python -m pip install python-dotenv==1.2.2 -e ./mcp
.venv/bin/python scripts/install_fingerprint.py --profile-home "$HOME/.hermes/profiles/myclipper"
HERMES_HOME="$HOME/.hermes/profiles/myclipper" hermes setup
HERMES_HOME="$HOME/.hermes/profiles/myclipper" hermes chat
```

The installer refuses an existing target, copies only authored SOUL/config/skills, and uses `hermes config set` to set `terminal.cwd` and a stdio MCP launcher explicitly scoped to the new profile. It never loads this author's keys or starts a gateway. Run it with your intended Python environment so its MCP dependencies resolve there. Configure your own model using setup; no model/provider account is exported.

### Native distribution / existing profile

`hermes profile install github.com/kofiowusuai-lab/clipping-fingerprint --name myclipper` installs the agent rules. For updates, follow the official profile distribution docs. Keep a separate persistent checkout for media executables and dependency installation. Set `terminal.cwd` to that checkout using the CLI. Install the repository's skills/SOUL intentionally if adding to an existing profile; do not overwrite customized profiles blindly.

For a distribution-installed profile, register the MCP launcher with an explicit Python and profile path (the launcher reads credentials itself, never from command-line token values):

```sh
hermes -p myclipper config set terminal.cwd /absolute/path/to/clipping-fingerprint
hermes -p myclipper mcp add supoclip --command /absolute/path/to/clipping-fingerprint/.venv/bin/python --args /absolute/path/to/clipping-fingerprint/scripts/fingerprint_mcp.py --profile-home /absolute/path/to/your/profile
hermes -p myclipper mcp test supoclip
```

Use the CLI version's `--help` and current official documentation when configuring Hermes. Restart only that profile if required; never restart all gateways.

## 3. Optional SupoClip service

The bespoke local creator/podcast renderers do not require a running web stack. The full upstream application is included for MCP-managed automatic tasks; read `docs/setup.md`, `docs/configuration.md` and `mcp/README.md` before starting it. The API/worker database, ASR provider and LLM provider must be configured independently of Hermes.

Choose your own authenticated API key, or a user ID and signed-header secret. Put only your own secrets in your private profile `.env`, not in committed config:

```dotenv
SUPOCLIP_API_URL=http://127.0.0.1:8000
SUPOCLIP_API_KEY=
# Or signed self-host headers, not both:
SUPOCLIP_USER_ID=
SUPOCLIP_AUTH_SECRET=
# Optional delivery:
TELEGRAM_BOT_TOKEN=
```

The launcher defaults to the local API, not a paid hosted endpoint. Its `.env` loading is restricted to SupoClip/backend-auth keys. Check `supoclip_health` and authenticated task listing before jobs. A successful unauthenticated health call does not prove that you can create tasks or run ASR/LLM analysis. Generate fresh database/auth/encryption secrets for the full app; do not deploy example values. No full-stack migration/restart is required just to run the local smoke.

The historical native-runtime docs/scripts are preserved as recipes. Their original compose/log/MCP environment assumptions are not the supported portable install path. Use the full upstream documented Docker route or adapt them explicitly; do not assume absent `.env.mcp.local` exists.

## 4. Real source workflow

1. Receive authorized local media or URL and campaign/audience requirements. Establish duration/eligibility/sound/branding constraints.
2. Coarse-to-fine source review: `python scripts/creator_analyze.py --source VIDEO --output FRESH_DIR` and optional correctly offset JSON3 captions. Inspect source audio, visuals and word provenance; proposals are never auto-approved.
3. Creator jobs: create a version-1 reviewed plan compatible with `creator_engine.py`. Use absolute input/output/font paths. `python scripts/fingerprint_creator.py --plan PLAN.json` is the fast single-word/persistent-hero path. For extra callouts/counters/supporting-video graphics use the full creator renderer instead. These overlay fields are not silent fallbacks in the atlas adapter.
4. For reviewed native-30fps multi-range stream edits, `render_ddg_batch_clip.py` accepts the retained batch-plan contract; the filename records its origin, not automatic DDG detection. Its fixed source layout/tweet-panel crop must be adapted to a new stream. Do not reuse episode-specific crops blindly.
5. Podcast jobs: follow `docs/podcast-pipeline.md`, `configs/podcast/schema.json` and the example. The example deliberately references absent user media/SFX and is unapproved. Provide your own inputs, remove optional riser/flash settings for a source-only edit, set actual reviewed shots/ranges and provenance. Run inspect, transcribe (if explicitly provisioned), shortlist/prepare/render/qa stages or `run` only after review. The smoke generates a complete source-only example config you can study.
6. Thinking pauses: `python scripts/trim_reviewed_pauses.py existing.mp4 --remove START:END ... --output-dir /absolute/fresh-dir`. Review each gap first and leave speech handles. This trims all burned layers and A/V together without changing speed. Never silently apply arbitrary silence thresholds to meaningful reactions or quiet speech.
7. Verify ffprobe/full decode, caption word order/onsets, complete opening/closing speech, extreme crops and every cut. Inspect the actual contact sheets/frames; technical QA leaves visual approval pending. Use source-frame and audio-waveform comparison for suspected sync issues.
8. Supply matching post copy/hashtags. Deliver to the operator only; campaign publishing is separate explicit authorization.

### Optional verified Telegram delivery

```sh
HERMES_HOME=/absolute/path/to/your/profile \
  .venv/bin/python scripts/deliver_clip.py /absolute/clip.mp4 --chat YOUR_CHAT_ID --caption 'Clip label'
```

Token comes from that profile's secret `.env`; chat must be explicit or supplied through `TELEGRAM_CHAT_ID`. There is no author's bot ID/chat/token. Keep playback copies below 19 MiB for Bot API getFile verification. Require `status=confirmed`, a message ID and `remote_readback=true`; a local file or text message is not video delivery. Supply the separate copyable post caption alongside the attachment.

## 5. Container jobs

`Dockerfile.fingerprint` is rendering-only. `Dockerfile.fingerprint.dockerignore` excludes credentials, live profiles, media caches, dependencies and unknown fonts from the build context. `compose.fingerprint.yml` mounts inputs read-only, outputs read-write, drops capabilities and disables runtime network. Ensure the output bind mount is writable by the image's UID 10001, or explicitly select your own uid/gid. Never fix permissions using broad recursive chmod on unrelated paths.

```sh
docker compose -f compose.fingerprint.yml build
# Parent directory should be writable by the configured container user:
docker compose -f compose.fingerprint.yml run --rm render smoke --output-dir /outputs/smoke-01
# A reviewed job must reference /inputs sources and /outputs destinations:
docker compose -f compose.fingerprint.yml run --rm render creator --plan /inputs/creator-plan.json
```

The container does not include an authenticated Hermes instance. Use Hermes on the host to invoke the renderer, or configure an independently authorized agent environment. No secrets need to be baked into an image. Do not claim an image security audit or cross-platform success solely because a native smoke passed.
