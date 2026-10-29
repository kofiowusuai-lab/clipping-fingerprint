# Creator analysis: coarse → targeted review

A standalone local CLI for finding **review cues**, separate from the podcast edit
format. It reads a completed local video; it does not download, transcribe, invoke
services, render a clip, alter Remotion, or change the processing backend. Uses the
existing backend Python environment (`numpy`, Pillow, OpenCV), FFmpeg and ffprobe.
No new dependencies or model downloads are required.

## Quick help and first pass

Run from the repository root:

```sh
backend/.venv/bin/python scripts/creator_analyze.py --help

# ONLY AFTER the video download has completed:
backend/.venv/bin/python scripts/creator_analyze.py \
  --source .local/uploads/youtube-cache/yHLNoTKOO4A/full.mp4 \
  --captions .local/uploads/youtube-cache/yHLNoTKOO4A/full.en-orig.json3 \
  --output outputs/creator-analysis/yHLNoTKOO4A-coarse
```

`--captions` is optional. All timestamps are original **source seconds**, not an
edited timeline. Use a fresh or empty output directory: existing analysis is never
silently overwritten. The CLI cannot determine whether another process is still
writing a video; completion of the download is the caller's prerequisite.

A successful exit and `manifest.json.complete: true` mean the technical scan
completed, **not** that any moment was approved. The manifest and proposals remain
`needs_review`. Failure may leave a partial output with `complete: false`; use a new
folder for a retry. Never treat a partial run as an approved or complete analysis.

## Output contract

| Artifact | Contents |
| --- | --- |
| `metadata.json` | Original ffprobe format and streams JSON, including duration, dimensions, codecs and audio streams. |
| `manifest.json` | Source path/size, duration, mode, completeness, contact counts and limitations. |
| `words.json` (with captions) | Envelope with `timebase: source_seconds`, `words: [{text,start,end,provenance}]` and complete original JSON3 at `provenance.original_json3`. |
| `transcript.txt` (with captions) | Readable timestamped text, roughly 12-second lines or separated by pauses. |
| `audio-features.json` | Every 0.5-second PCM window's RMS, peak, transient, actual end, percentile thresholds and candidate cues; absent audio is explicit, not fabricated. |
| `visual-features.json` | Every 1-second sample's normalized luma, grayscale absolute-difference motion, RGB histogram distance, thresholds and sample-indexed cues. |
| `scoretimes.json` | All audio/scene/motion candidate cues with feature values sorted chronologically; **not a quality ranking**. |
| `proposals.json` | Chronological bounded windows with original cue evidence, `status: needs_review` and explicit handle/merge policy. |
| `contacts/index.json` | Source-second timestamp, sample index, sheet filename and zero-based slot for every thumbnail. |
| `contacts/sheet-NNN.jpg` | 4×5 sheets, at most 20 frames per sheet, each image fitted within 480×270 with a separate timestamp strip. |

Consumers should read `words.json["words"]` rather than treating the envelope as a
bare list. Word timing is inferred, not forced aligned. No speaker labels exist.
The complete untouched cache and each word's original segment survive in provenance
so display cleanup can be audited without losing source evidence.

### Caption normalization

YouTube JSON3 uses `events[].tStartMs` plus `segs[].tOffsetMs`; both are converted
from milliseconds to source seconds. Segment text containing multiple words is
spread over the available interval. A strictly later segment offset bounds its
end, otherwise event duration is used, otherwise a conservative tail (up to 1.5s)
is inferred. Global chronological processing shortens overlapping ends and shares
an interval between equal-start words. All emitted words have positive duration,
nonoverlapping intervals and bounds within the source.

Whitespace/newline display events contribute no words. HTML/display tags, `>>`,
bracketed and parenthesized transcript cues and music glyphs are removed; original
unclean text is retained. Parenthesized/bracketed cleanup is deliberately
conservative and can also discard parenthesized speech: inspect original provenance
and listen before publishing. YouTube ASR can omit profanity, mistranscribe names,
repeat rolling captions or miss speech altogether. Cleanup does not repair ASR,
identify speakers, or certify accurate caption timing. No paid transcription or
fallback ASR is invoked.

## Audio and visual signals

Audio is decoded sequentially to mono 8 kHz signed 16-bit PCM. Each 4,000-sample
window yields linear full-scale RMS, peak and the maximum absolute adjacent-sample
change (including the boundary with the preceding window). Energy candidates use
the source's RMS 90th percentile with a 0.015 floor. Transient candidates use the
95th percentile with a 0.05 floor. These values and the selected thresholds are
saved. Quiet/silent media do not automatically become events just because the
percentile is zero. Candidates can be frequent in uniformly loud media.

The visual pass is a sequential FFmpeg raw RGB pipe, not repeated full-resolution
seeks. It emits a nominal 1 fps grid fitted to 320×180. Each sample has mean luma,
mean grayscale absolute difference from the previous sample, and normalized
8×8×8 RGB-histogram L1 distance (divided by two). Histogram distance >=0.30 proposes
a scene-change sample. Motion at/above its 95th percentile with a 0.08 floor
proposes a motion-change sample. The first frame has zero deltas. These are
**sample-indexed differences**, not exact edit boundaries or optical flow.

The second sequential video pass produces contact thumbnails, by default every
20 source seconds. A 1,960-second source has 98 nominal timestamps (0 through
1,940), split into five sheets. Only one sheet, the current image and a small
previous-frame/histogram state are held; no full-source frame cache is built.
FFmpeg decoding is single-thread limited. Full-resolution decoding still costs
CPU, but no full-source decoded frames are retained. Audio scalar features and
visual scalar features remain small lists in memory.

Sampling uses an explicit FFmpeg FPS grid with upward timestamp rounding so the
first coarse thumbnail corresponds to source start rather than half an interval
later. Labels refer to the nominal grid, not exact packet PTS. The selected frame
is the preceding decoded frame; the final frame can repeat to complete a grid
near EOF. Review timestamps are similarly source-relative and approximate within
source-frame sampling. Targeted decoding may read a small lookahead beyond the
last grid time. Rapid events between samples can be missed completely.

### Proposal policy

Nearby cues cluster within 3 seconds, with 4 seconds of pre-handle and 8 seconds
of post-handle. Windows extend to at least 10 seconds when the source permits,
never exceed 35 seconds, and clamp to source bounds. Overlapping/touching windows
merge only if their union remains <=35 seconds. Dense cue runs split; adjacent
windows may still overlap to retain context. A source shorter than 10 seconds
necessarily yields shorter windows. The original cues and feature values remain
attached, so a human can see why a window was proposed.

No probabilities, virality scores, joke detection, action labels, kills, dramatic
beats, audience reactions or payoff claims are invented. Loud music, applause,
compression, lighting changes, camera motion and edits can all trigger these
cues without an interesting moment. Conversely, a quiet line can be the best
moment and generate no cue. Periodic contacts and transcript review complement,
not replace, the cue proposals.

## Targeted review (finer images; no full-source rescan)

```sh
backend/.venv/bin/python scripts/creator_analyze.py \
  --source /absolute/completed-source.mp4 \
  --output outputs/creator-analysis/review-120-145 \
  --start 120 --end 145 --interval 0.5

# Optional bounded face-detection inspection, using the existing bundled model:
backend/.venv/bin/python scripts/creator_analyze.py \
  --source /absolute/completed-source.mp4 \
  --output outputs/creator-analysis/review-120-145-faces \
  --start 120 --end 145 --interval 1 --faces
```

Both `--start` and `--end` are required for review; they must satisfy
`0 <= start < end <= duration`. Default review interval is 1 second; default
coarse contact interval is 20 seconds. CLI intervals must be >=0.1 seconds.
Review produces metadata, manifest and contacts, plus normalized captions if
requested; it does **not** repeat audio or whole-source visual feature extraction.

`--faces` is permitted only on review sections <=120 seconds with <=240 sampled
frames. YuNet runs only on those 480×270 samples, not every source frame. It uses
`backend/src/media/models/face_detection_yunet_2023mar.onnx`, or a supplied existing
`--face-model`; a missing model errors rather than downloading. Bounding boxes
are in letterboxed thumbnail pixels and the model's detection confidence is
reported only as detection confidence, never editorial quality. Small/occluded
faces may be missed. Multiple stage people and reactions need manual inspection:
face detection is **not speaker identification**, speaking detection, identity,
reaction understanding, framing approval or a crop plan.

## Keep the stages separate

1. **Media:** completed original source and original caption cache. Immutable inputs.
2. **Analysis:** this CLI's metadata, normalized transcript, measured cues and review
   sheets. No source mutation, selected clips, publishing or paid calls.
3. **Clip plan:** a human listens/watches actual proposed and uncued sections,
   establishes truthful hook → pacing → payoff, chooses precise source ranges,
   context, speaker/reaction coverage, reframing and caption corrections. The plan
   must explicitly record selections; `needs_review` proposals are not a plan.
4. **Render:** a separate editor/composer consumes an approved plan and creates an
   actual clip. Creator choices do not inherit the podcast format automatically.
   This analyzer does not modify the Remotion/render pipeline.
5. **QA:** verify the actual rendered audio, cuts, captions, faces/context, safe areas,
   duration and frame integrity; technical scan completion is not delivery approval.

## Technical tests

```sh
backend/.venv/bin/python -m unittest discover -s scripts -p test_creator_analyze.py -v
```

Tests cover JSON3 offsets, cue cleanup and raw provenance, missing durations,
overlap repair, merging/time bounds, short sources, real FFmpeg audio and visual
features, sheet splitting, targeted review and the bundled YuNet path. They generate
only a disposable **two-second synthetic technical fixture** with motion and a tone.
It is not real source footage, highlight evidence or proof of editorial quality.
No in-progress source or captions are read by the test suite.
