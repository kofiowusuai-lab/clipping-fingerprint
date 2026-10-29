# Manual podcast pipeline (JSON v1)

`scripts/podcast_pipeline.py` is an optional local CLI, not a replacement for the API/worker or existing episode scripts. It makes supplied editorial decisions reproducible. **It is not an automatic highlighter, speaker recognizer, reaction selector, source downloader, or publisher.** No credentials, paid services, model downloads or browser downloads are requested.

## Contract and new-source flow

- Machine-readable schema: [`configs/podcast/schema.json`](../configs/podcast/schema.json).
- Editable, deliberately **unapproved** example: [`configs/podcast/example.json`](../configs/podcast/example.json). Replace illustrative ranges, crops and paths before processing; it is not a Dana edit.
- All filesystem paths are relative to the **config file**, not your working directory. All job paths written for Remotion are absolute. URLs are provenance only; processing requires a separately acquired local `source.path`. An output directory cannot contain an input.
- `version: 1`; default `width:1080`, `height:1920`, `fps:30`, prepared footage `crf:19` (18 also allowed). `fontPath` is explicit; use the approved `backend/fonts/Poppins-ExtraBold.ttf`.
- `transcript.path` is an array or `{ "words": [...] }`; each word has `text`, `start`, `end`. `transcript.units` must explicitly be `milliseconds` (existing YouTube caches) or `seconds`. Ranges/shots are **always source seconds**. Track times are **shot-relative seconds**, crop coordinates are source pixels.

From the repository root:

```sh
# Copy example.json to configs/podcast/episode.json and edit source/font/output paths.
backend/.venv/bin/python scripts/podcast_pipeline.py inspect --config configs/podcast/episode.json

# Reuse an existing cache whenever available. Otherwise transcribe with an
# EXISTING trusted local checkpoint, never a model name/download. Limit a first
# pass to a manageable source section; timestamps retain the source offset.
backend/.venv/bin/python scripts/podcast_pipeline.py transcribe \
  --config configs/podcast/episode.json \
  --model-path .local/cache/whisper/tiny.en.pt \
  --transcribe-start 0 --transcribe-end 600

# Supply candidate clips/ranges/notes yourself, then produce approval material.
backend/.venv/bin/python scripts/podcast_pipeline.py shortlist --config configs/podcast/episode.json
```

`transcribe` uses local Whisper CPU inference with word timestamps; it writes the configured cache in its declared units. It refuses to replace an existing cache without `--force-transcript`. A section transcription is a section-only cache, not a full-episode transcript. Full-source transcription is possible by omitting `--transcribe-end`, but consumes time/memory and is not automatically invoked by `run`. To add sections, merge/review source-timestamped caches yourself; this CLI does not silently append or merge. Whisper ASR is not accurate editorial verification, diarization or speaker ID. Load only trusted `.pt` files.

Review the actual source before setting each clip's:

```json
"approval": {
  "approved": true,
  "reviewer": "Editor name",
  "reviewedAt": "2026-10-28T12:00:00Z"
}
```

The CLI never approves a clip. `shortlist.json` is review material containing the supplied editorial JSON, not machine-chosen moments. `run` writes it then blocks processing of unapproved clips. Record truthful `headline`, `sourceNotes`, `payoff`, and `postCaption` (including desired hashtags) for every clip. Identify complete hook → pacing → payoff, preserve consonant onsets with source handles, remove quote-card/random inserts through approved ranges, and verify the actual closing sentence. No automatic pause deletion occurs.

```sh
backend/.venv/bin/python scripts/podcast_pipeline.py prepare --config configs/podcast/episode.json --only 01-example --resume
backend/.venv/bin/python scripts/podcast_pipeline.py render  --config configs/podcast/episode.json --only 01-example --resume
backend/.venv/bin/python scripts/podcast_pipeline.py qa      --config configs/podcast/episode.json --only 01-example --resume

# Equivalent sequence: inspect, shortlist, prepare, render, qa; NOT transcribe.
backend/.venv/bin/python scripts/podcast_pipeline.py run --config configs/podcast/episode.json --resume
# --only accepts repeated flags or comma-separated exact clip ids.
```

## Ranges, camera boundaries and safe framing

Each clip's `ranges` is an ordered list of `[start,end]` source-second audio keep ranges; reordered opening hooks are supported without relabeling original chronology. Each range duration is rounded independently to the nearest output frame. PCM is padded/trimmed to that range's exact frame duration, and captions use the same quantized cumulative offsets. Preserve natural audio handles yourself; word timestamps are not safe edit boundaries. Words beginning before a keep range are not manufactured into complete words. Overlapping/unordered transcript words are rejected rather than silently repaired; correct the cache against source audio.

Optional `shots` must partition **every range exactly** in the array order. An empty array creates one auto shot per range. Supply a separate shot for every source-camera cut: the CLI does not detect scene cuts and must not interpolate a crop across different cameras. A shot uses `rangeIndex` (zero-based), source-second `start`, source-second `end`, and `mode`:

- `contain`: entire source frame, aspect-preserved on black. Safe fallback; not a claim of finished creative framing.
- `auto`: bundled YuNet only, sampled approximately once per second including near endpoints. Every sampled frame must have exactly one face, otherwise the **whole shot** uses contain. Single-face crop positions are smoothed across neighboring samples. If a sampled face/hair safety margin does not fit, use contain. Unavailable model/import also uses contain; no model is downloaded. This cannot distinguish an interviewer from a speaker, identify source quote cards, or rule out between-sample glitches.
- `crop`: manually reviewed `crop:{x,y,width,height}` and `reviewed:true`, optionally `track:[{time,x,y},...]`. Fixed crop size, linearly interpolated smoothed positions; source-pixel bounds are checked. Change crop size by making another purposeful shot. Coordinates outside the frame are rejected. Dimensions are rounded down to even pixels for H.264.

`reaction:true` enforces a minimum three-second hold. The CLI does not decide whether it is a genuine or appropriate contemporaneous reaction.

### Finish a word without a subsecond listener flash

A reviewed shot can set `videoEnd` before `end`; its last safe source frame freezes through the remaining timeline while the original range audio continues unchanged. No repeated video/audio source range is inserted. Automatic face sampling stops at `videoEnd`, not the incoming camera. For example, when a host cut is at approximately 1258.54 and dialogue needs to continue to 1258.72:

```json
{"rangeIndex":0,"start":1250.0,"end":1258.72,"videoEnd":1258.50,"reviewed":true,"mode":"auto"}
```

Use a deliberately safe pre-cut `videoEnd`, inspect the retained last frame and avoid long/obvious freezes. The CLI floors retained picture-frame count to keep camera-cut footage out. No `tailHold` config is needed: `end-videoEnd` is the hold, reported as `tailHold` in `prepare.json`. It does not shorten audio or change caption offsets.

## Clean audio and the one graphics pass

`prepare` encodes uncaptioned high-quality H.264 picture parts at CRF 18/19, concatenates them by stream copy, then deletes duplicate part files. Retained archival assets are `picture.mp4`, clean assembled speech/effects `mix.wav`, normalized `normalized.wav`, `words.json`, and `prepare.json` (crop plans, frame counts and both loudnorm measurements). No ProRes intermediates.

Source audio is decoded to 48 kHz stereo float PCM per keep range and concatenated **before AAC**, avoiding per-shot AAC encoder delay. Optional supplied `riser` uses `path`, reviewed `crestSeconds`, `cutSeconds`, `gain` and `semanticNote`. It is back-timed so its audible crest lands at the completed-hook range boundary; its quiet tail is discarded, not speed/pitch shifted. It must fit before that boundary. A minimal 1 ms tail taper avoids an abrupt sample discontinuity. The CLI neither selects sound effects nor assumes a container's end is its audible crest. Remove `riser` to use clean dialogue only.

Audio uses FFmpeg loudnorm **two passes** (`I=-16`, `TP=-1.5`, `LRA=11`); measurements and actual normalization mode are recorded. Silence/nonfinite loudness is a failure, not a fictitious pass. `render` sends uncaptioned `picture.mp4` and remapped words through **one** local `node remotion/render.mjs JOB` graphics render. The final FFmpeg step video-copies that graphics result, encodes normalized PCM once to AAC 192k, and adds `+faststart`. It never burns a second subtitle/effects encode over an already captioned export.

`captions` maps existing `style`, `headlineDuration`, `headlineAccent`, and `strikeWords`. Standard `headline` and the explicit font are passed unchanged. Approved typography ratios belong to the Remotion implementation, not Python text drawing. `graphics` is **editorial metadata only**; it does not guess JS fields. Top-level then per-clip `renderOptions` merge into the job, and the renderer's actual JS schema owns optional prop validation. Python prohibits overriding paths, words, dimensions, fps, duration or `frameRange` to preserve the timeline. Unknown options are not proof a graphics feature exists: inspect `remotion/schema.mjs` and confirm visible behavior.

**Encoding boundary:** Python's `crf` controls prepared footage only. The current local `remotion/schema.mjs` and `render.mjs` support a nested renderer options object. Set the pipeline's top-level or per-clip merge dictionary to:

```json
"renderOptions": {
  "renderOptions": {"crf": 18, "muted": true, "audioBitrate": "192k"}
}
```

The outer object merges job props; the inner object is the renderer's actual encoding contract. This requests archival CRF 18 graphics and skips unnecessary Remotion audio, since final mux supplies normalized PCM. Without that nested CRF setting the renderer defaults to 21; a later video-copy mux cannot improve it. No Python renderer fork or guessed encoding prop is used. Any optional asset `imagePath`/`videoPath` supplied through graphics options must already be absolute local paths as required by JS. Similarly, riser audio does not itself create a white flash: pass supported `transitions` in the outer merge dictionary, then verify their semantic timing visually.

## Resume and verification

`--resume` requires stage receipts with matching config/input metadata/code fingerprints, SHA-256 of **every** retained output, and full decode of media. Merely finding an MP4, partial job output, or stale receipt is insufficient. Render depends on a verified prepare receipt; QA depends on verified prepare and render receipts. Failure clears that stage's receipt before work begins. Input fingerprints use resolved paths, sizes and nanosecond mtimes (not full multi-hour source hashing), plus config and pipeline/Remotion source hashes. Restore-preserving-size/mtime source changes are not detected; invalidate receipts manually if external tooling rewrites inputs while preserving metadata. Resume is conservative: any config edit may invalidate more clips/stages than strictly needed.

`qa` writes:

- `qa.json`: ffprobe streams, dimensions/fps/exact known frame count and A/V duration checks, full FFmpeg decode, decoded-audio RMS/peak and dBFS, blackdetect/silencedetect event logs.
- `contact-sheet.jpg`: first/quarter/middle/three-quarter/last frames plus before/on/after every supplied shot and range boundary. Reports contain actual timestamps.
- **Always** `visualReview:"pending"`, `deliveryReady:false`. A successful technical QA is not visual/editorial/audio approval. Black/silence detections are review flags, not silently classified defects.

Automated decode cannot catch all visual corruption. Before delivery, also run the existing all-frame regression checker, with explicitly reviewed effect-frame exclusions where necessary:

```sh
backend/.venv/bin/python scripts/check_remotion_frames.py \
  outputs/podcast-example/01-example/picture.mp4 \
  outputs/podcast-example/01-example/final.mp4 \
  --report outputs/podcast-example/01-example/all-frame-check.json
```

That checker measures a central picture band and can legitimately flag overlays/effects there; do not hide failures by inflating thresholds. Review every transition/effect and listen to opening/closing words; ensure the right speaker, framing, no source cards, readable captions/hero and complete payoff. Contact sheets have not been visually inspected just because the CLI generated them. Publishing/delivery, manual review signoff and platform experiments remain separate. `post-caption.txt` accompanies each completed render.

## Tests

```sh
backend/.venv/bin/python -m unittest discover -s scripts -p test_podcast_pipeline.py -v
# Real synthetic-source encode, prepare, ONE Remotion render, mux, QA and resume:
PODCAST_INTEGRATION=1 backend/.venv/bin/python -m unittest discover -s scripts -p test_podcast_pipeline.py -v
backend/.venv/bin/python scripts/podcast_pipeline.py --help
```

Integration needs local FFmpeg/ffprobe, the existing backend NumPy/Pillow environment, the installed Remotion Node dependencies and local Chrome (or `REMOTION_BROWSER_EXECUTABLE`). It uses a temporary tiny synthetic source, never Dana or another real episode, and cleans its media afterward. Existing episode-specific scripts are not imported or changed.
