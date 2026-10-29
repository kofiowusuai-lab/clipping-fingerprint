# Premium podcast prototype: running another episode

This extends the existing local SupoClip checkout. It is an **editor-assisted local workflow**, not a newly deployed web platform, automatic viral-moment detector, publisher, or reliable speaker recognizer. No frontend/worker replacement, gateway restart, paid activation, or new model download is required.

## Responsibilities and stages

1. **Source inspection:** acquire an authorized local source; record provenance and run ffprobe. Keep the untouched source outside the output directory.
2. **Transcription/timestamping:** reuse reviewed word caches; otherwise use `podcast_pipeline.py transcribe` with an existing trusted Whisper checkpoint. Source times and units are explicit. Check selected speech independently; YouTube captions are not an accuracy guarantee.
3. **Candidate selection:** editor reviews transcript/context and records the hook, main idea, payoff, exact keep ranges, and source-camera boundaries. Do not invent statements, remove essential context, or pad weak moments to make three clips.
4. **Approval/selection:** inspect source footage, complete the approval metadata in the JSON, and retain rejected candidates and reasons separately. Approval here concerns an edit plan, not final visual QA or K's individual endorsement.
5. **Cutting/reframing:** FFmpeg prepares frame-aligned picture and PCM audio. Use reviewed crop tracks or conservative single-face assistance. Separate source-camera shots. Contain the whole frame when uncertain; review that fallback rather than calling it a polished final edit.
6. **Captions/graphics:** Remotion receives the prepared video, remapped words, style and optional graphics. Fonts, grouping, positions, colours, key-word motion, strikes, lower-thirds, hooks, graphics/endcards, backgrounds and transitions are configurable. Do not invent a brand or add effects merely to show that they exist.
7. **Final render:** one Remotion graphics pass, followed by FFmpeg video-copy mux with normalized PCM encoded once to AAC. No second full subtitle/flash encode. CRF18 final H264 plus retained uncaptioned CRF19 picture and 24-bit normalized WAV form a practical local archive.
8. **QA:** full decode/probe, exact frame count/duration, audio levels and sync, black/silence events, contact sheets, all-frame picture comparison with only reviewed effect exclusions, then actual rendered-frame/editorial review. Fix discovered defects. Technical QA deliberately does not auto-approve visual quality.
9. **Delivery:** use the profile-local verified uploader for each selected MP4, confirm the remote file, and provide matching copyable post text and hashtags. Publishing still requires K's permission.

## Quick start on this machine

From `/workspace`:

```sh
# Copy configs/podcast/example.json to a new episode config, then edit paths.
# Paths in configs are relative to that CONFIG FILE, not to the shell directory.
backend/.venv/bin/python scripts/podcast_pipeline.py inspect --config configs/podcast/episode.json

# Only when a reviewed cache is not already available. Existing model only.
backend/.venv/bin/python scripts/podcast_pipeline.py transcribe \
  --config configs/podcast/episode.json \
  --model-path .local/cache/whisper/tiny.en.pt

# Enter editorial ranges/notes/shots, review source and approve each candidate.
backend/.venv/bin/python scripts/podcast_pipeline.py shortlist --config configs/podcast/episode.json
backend/.venv/bin/python scripts/podcast_pipeline.py run \
  --config configs/podcast/episode.json --resume
```

Use `--only exact-clip-id` to isolate a candidate; separate `prepare`, `render`, and `qa` commands are also available. `run` never silently transcribes a full source or selects/approves highlights. `--resume` requires matching fingerprints, output hashes and decodable media; code/config changes intentionally invalidate receipts. Optional graphics assets are fingerprinted too. Source/transcript/font/graphics aliases are rejected to prevent input destruction. CLI guards are not a hostile multi-tenant security sandbox.

## Styles and optional graphics

- `configs/visuals/podcast-bold.json`: approved Poppins ExtraBold800, captions width*.095, hero width*.075, yellow spoken-word highlights and restrained entrance. At1080 the type scales with the frame; approved relative sizing is preserved.
- `configs/visuals/podcast-clean.json`: optional comparison, same font-size ratios and position, sentence case/cyan accent/no scale entrance. It does not replace the approved default.
- These are **property templates**, not full pipeline configs. Remove their `description` key, then merge into top-level/per-clip `renderOptions` in the pipeline JSON. Per-clip options override top-level keys (nested objects are not deep-merged; copy the complete nested caption style when overriding it).
- Full graphics contract: `remotion/test/GRAPHICS-CONTRACT.md`.
- Full CLI/JSON contract and validation: `docs/podcast-pipeline.md`, `configs/podcast/schema.json`.
- Negative-list emphasis stays inline and sequential: only the relevant spoken word turns red and is crossed out. Earlier nouns never accumulate into a replacement list. Positive lists should use highlighting instead of misleading negation.
- Endcards replace picture inside their configured interval: they do not automatically append time or silence. Keep them disabled unless there is a reason and verified branding/CTA assets.
- Supporting-video layouts accept separately prepared synchronized local footage. The second video's audio is muted. There is no automatic supporting-visual search, semantic placement, lip sync, or multi-camera synchronization.

## Speaker and audio limitations

The repository already contains diarization-driven mouth-motion framing, but tiny.en does not provide dependable speaker labels and face detection alone cannot identify who is talking. This prototype uses manually reviewed camera boundaries and crop plans on Dana. Reliable diarization needs a separately evaluated diarizer, a proven mapping to visible faces, representative multi-person tests, and explicit review. No gated model, new large model or paid provider was activated. Manual speaker labels/coverage and safe whole-frame fallbacks are the reliable available alternatives.

Dialogue is normalized with two-pass FFmpeg loudnorm targeting -16 LUFS, -1.5 dBTP, LRA11; actual measurements are retained. No automatic denoising or music bed is applied to clean studio speech. The supplied riser is the existing K-directed asset, not a new music licence grant. Its audible crest is back-timed to a completed-hook cut without pitch/speed changes. Any graphic bloom is applied in the same Remotion pass, not layered over an already-flashed video.

## Commercial use and source quality

Current Remotion v4 terms were checked at https://www.remotion.dev/license: individuals, nonprofits and for-profit organizations up to3 employees qualify for its free licence, including commercial video creation. Larger for-profit organizations require a company licence; evaluation is allowed separately. K's organization eligibility has not been established. Nothing was purchased or activated. Recheck before commercial rollout, especially across a major-version upgrade. Preserve SupoClip's own licence; Remotion is not automatically relicensed under it.

The cached Dana source is AV1 1920x1080/24fps, Opus48k stereo, with a low video bitrate. Portrait crops necessarily upscale a smaller region; exporting1080x1920 cannot reconstruct detail absent in that source. A higher-quality authorized master is the best upgrade. Source rights, supplied-sound rights and brand/font entitlement remain separate from having a functioning renderer. No external publishing has occurred.

## Verification commands

```sh
cd remotion && pnpm run typecheck && pnpm test
# Return to the repository root.
backend/.venv/bin/python -m unittest discover -s scripts -p 'test_podcast*.py' -v
# Optional real FFmpeg/Remotion/Whisper integration tests:
PODCAST_INTEGRATION=1 backend/.venv/bin/python -m unittest discover -s scripts -p test_podcast_pipeline.py -v
```

For the Dana example, see `outputs/premium-dana/pipeline.json`, source audit/transcript timing edits, the selected/rejected editorial shortlist, and each clip's `prepare.json`, `render.job.json`, `qa.json`, comparison reports and review frames. A CLI-generated `visualReview: pending` is deliberate; a separate actual-output review is required before delivery.
