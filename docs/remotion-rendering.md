# Optional local Remotion rendering layer

Remotion 4.0.539 is an isolated Node/React renderer under `remotion/`. It is **opt-in**, not connected to FastAPI task processing, the automatic worker or the Next.js editor. Existing FFmpeg jobs and frontend dependencies/lockfile are unchanged.

## Responsibilities

1. Existing Python/FFmpeg workflow selects complete passages, cuts pauses, tracks/crops speakers and prepares an MP4 with original audio, **without burned captions**.
2. Export clip-relative word timings in **seconds**.
3. `scripts/render_with_remotion.py` invokes the Node renderer with the prepared MP4 and words.
4. Remotion renders word-timed typography and optional headlines. The adapter probes and fully decodes the resulting H.264/AAC MP4 before reporting success.
5. Review actual opening/closing frames, caption readability and speaker framing, then use the verified Telegram uploader and include copyable post text. Rendering does not select good segments, validate campaign rules or verify delivery.

## Install / verify

```sh
cd remotion
pnpm install --frozen-lockfile
pnpm run typecheck
pnpm test
```

Node 22 and pnpm 11.24.0 were used for verification. All Remotion packages are pinned to exactly the same version. The separate lockfile avoids modifying SupoClip's frontend dependencies. `pnpm-workspace.yaml` allows only esbuild's required install script; do not broadly approve dependency scripts. Initial installation reported a schema-utils/webpack peer-version warning; typecheck, unit tests and real video rendering passed with the locked tree. Review dependency changes rather than updating packages independently.

The renderer uses `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`, or the path in `REMOTION_BROWSER_EXECUTABLE`. It fails if that executable is absent rather than silently downloading a browser. No cloud service, API key or paid provider is used.

## Render from repository root

```sh
backend/.venv/bin/python scripts/render_with_remotion.py \
  --video outputs/remotion-smoke/prepared.mp4 \
  --words outputs/remotion-smoke/words.json \
  --output outputs/remotion-smoke/bold-preview.mp4 \
  --style bold \
  --headline 'WANT MORE FREE TIME?'
```

Use `--style clean` and omit `--headline` for a steadier white-caption treatment. These are two starting presets, not an instruction to use the same style across niches. The initial local font is Poppins ExtraBold; `--font /absolute/font.ttf` supports another locally licensed TTF/OTF. Clean mode changes colour, scale and animation, but does not automatically switch to Montserrat. Campaigns restricting outside hooks should omit the headline, and no risers, flashes, music or stock footage are added by this renderer.

Word input can be an array or `{ "words": [...] }`:

```json
[{"text":"If","start":0.149,"end":0.39},{"text":"you're","start":0.39,"end":0.55}]
```

Times are relative to the **edited video**, nonoverlapping and sorted, and must fit its duration. Existing millisecond transcript caches require conversion/remapping first. Caption words longer than 40 characters are rejected for layout safety. Video should already use the desired aspect ratio; this layer deliberately does not make face-framing decisions. Output is rendered at 30 fps and retains the prepared video's dimensions.

`*.job.json` records each job; `*.verification.json` records actual probe/decode checks. Input media/font assets are staged in a temporary public folder rather than exposing the repository or secrets to the browser. Staging/bundle files are deleted after rendering. Jobs run locally; do not treat this CLI as an authenticated public rendering API.

`pnpm run studio` opens the composition editor for development; the default composition has no media. The production adapter stages each job transiently, so Studio is not yet a persistent media/project editor. No frontend Player integration or automated queue integration is implemented.

## Frame-capture correction and delivery gate

The first smoke renders listed below contained isolated repeated-horizontal-strip frames. Decode, audio checks and sparse review images missed them; they are **regression fixtures, not approved delivery files**. Do not reuse them as finished clips.

`render.mjs` now uses PNG screenshot capture with shared-memory capture disabled, parallel encoding disabled and concurrency one. The exact underlying Chromium failure is not conclusively identified, but this conservative path eliminated the reproduced corruption in the full rerender.

Before effects, compare every frame of the prepared input and captioned output:

```sh
backend/.venv/bin/python scripts/check_remotion_frames.py \
  outputs/remotion-corrected/prepared-full.mp4 \
  outputs/remotion-corrected/captioned-full.mp4 \
  --report outputs/remotion-corrected/all-frame-comparison.json
```

This measures an overlay-free central picture band; adapt the mask for different layouts. The original broken preview fails this gate, while the corrected full clip passed all 610 frame comparisons. Validate intentional flash frames separately rather than treating them as corruption or exempting unexplained errors. Final proof is under `outputs/remotion-corrected/`, including `final-frame-comparison.json`, `audio-check.json`, `transition-review.jpg` and `verification.json`.

The corrected full Dana edit preserves the approved riser mix and white bloom at 7.9 seconds. It retains the bold preview's Poppins ExtraBold font and sizes: captions `width*0.095`, headline `width*0.075`. Adding Remotion does not justify omitting approved effects from a complete edit; keep campaign restrictions authoritative.

## Initial evaluation artifacts (superseded by corrected outputs)

- `outputs/remotion-smoke/clean-preview.mp4`
- `outputs/remotion-smoke/bold-preview.mp4`
- `outputs/remotion-smoke/qa-summary.json`
- `outputs/remotion-smoke/clean-review.jpg`
- `outputs/remotion-smoke/bold-review.jpg`

Both real-footage renders were 720×1280, approximately eight seconds, H.264/AAC, passed full decode and A/V-duration assertions. Source/final audio correlation exceeded 0.9998. Both review sheets were visually checked. Eight job-validation tests and TypeScript checks passed. This is a technical evaluation using an already downloaded Dana White passage, not a newly selected campaign submission or an untested claim of complete automatic editing.

## Licensing / distribution

Read https://www.remotion.dev/license before commercial rollout or redistribution. At evaluation time its v4 terms allowed individuals, for-profit organisations with up to three employees, nonprofits and non-commercial evaluation to use it without payment. Larger for-profit organisations require a company license. No company eligibility is assumed and no paid license has been purchased/activated. Remotion has its own license; do not describe it as MIT or automatically relicense it under SupoClip's AGPL. The existing SupoClip license remains intact.
