---
name: creator-source-analysis
description: Use when scanning creator videos for local review cues.
---

# Creator source analysis

- Read `${CLIP_ROOT}/docs/creator-analysis.md` for the CLI/output contract before use.
- Wait for completed local media; never probe an in-progress download. Run `backend/.venv/bin/python scripts/creator_analyze.py --source VIDEO --output FRESH_DIRECTORY` from the repository root. Add `--captions JSON3` when available.
- Require successful process exit and `manifest.json.complete: true`; proposals remain `needs_review`, not editorial approval. Use a fresh output folder after failure to prevent stale artifacts.
- Inspect measured source audio and visual cues, periodic contact sheets and normalized transcript together. Loudness, motion and scene differences are review cues, not joke/kill/action detection or virality rankings.
- When reviewing a downloaded excerpt, keep its archive offset explicit. Full-archive JSON3 timestamps must be remapped before supplying captions to an excerpt analyzer; otherwise omit `--captions` and keep the original archive word cache separate. Never interpret archive-second captions as excerpt-relative timing. Inspect the first spoken line against the actual excerpt before planning captions.
- Preserve the transcript's lexical order when refining word timestamps. Mixing matched local-ASR times with unmatched cache times can reverse neighbouring words or collapse articles below one output frame. Reject reordered token sequences and sub-frame intervals before rendering; use a coherent timing source or repair bounded groups, not a final timestamp sort that silently changes the sentence. Local tiny.en is an independent speech check, not a proven forced aligner.
- Read normalized word records at `words.json["words"]`; source seconds are inferred from JSON3 offsets. Original unclean JSON3 remains in provenance. Verify chosen speech before captions or edits.
- Use `--start S --end E --interval 0.5` for targeted images. YuNet `--faces` is limited to review <=120 seconds and <=240 samples, with an existing local model; detection does not identify a speaker.
- Keep media, analysis, human clip plan, rendering and rendered QA distinct. This CLI does not change Remotion or render actual source clips.
- Preserve explicit FFmpeg FPS `round=up`, frame-count limiting and EOF padding: nearest timestamp rounding can label an interval-midpoint image as source start, while output-duration limiting can omit the final sample. Test the first sample against the actual first decoded frame.
- Validate changes with `backend/.venv/bin/python -m unittest discover -s scripts -p test_creator_analyze.py -v`. Tests generate disposable two-second technical fixtures only, never highlight evidence.
