#!/usr/bin/env python3
"""Local, bounded-memory creator source analysis; cues require human review."""
from __future__ import annotations

import argparse
import html
import json
import math
import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "backend/src/media/models/face_detection_yunet_2023mar.onnx"


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def probe(source: Path) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                             "-of", "json", str(source)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def clean_caption(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<[^>]*>", " ", text)
    text = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", text)
    text = text.replace(">>", " ").replace("♪", " ").replace("♫", " ")
    return " ".join(text.split())


def normalize_json3(data: dict, duration: float) -> dict:
    """Infer word intervals from segment offsets; preserve complete original cache."""
    candidates = []
    for ei, event in enumerate(data.get("events", [])):
        base = max(0.0, float(event.get("tStartMs", 0)) / 1000)
        event_end = min(duration, base + max(0, float(event.get("dDurationMs", 0))) / 1000)
        segments = event.get("segs", [])
        for si, segment in enumerate(segments):
            raw = segment.get("utf8", "")
            tokens = clean_caption(raw).split()
            if not tokens:
                continue
            start = base + max(0, float(segment.get("tOffsetMs", 0))) / 1000
            if start >= duration:
                continue
            following = [base + float(s["tOffsetMs"]) / 1000
                         for s in segments[si + 1:] if "tOffsetMs" in s]
            # Use next strictly later offset, else event duration, else conservative tail.
            ends = [t for t in following if t > start]
            end = min(duration, min(ends) if ends else
                      (event_end if event_end > start else start + min(1.5, .35 * len(tokens))))
            step = (end - start) / len(tokens)
            for wi, token in enumerate(tokens):
                candidates.append({"text": token, "start": start + wi * step,
                                   "end": start + (wi + 1) * step,
                                   "provenance": {"event_index": ei, "segment_index": si,
                                                  "raw_segment": raw, "inferred_timing": True}})
    candidates.sort(key=lambda word: (word["start"], word["provenance"]["event_index"],
                                      word["provenance"]["segment_index"]))
    words = []
    index = 0
    while index < len(candidates):
        stop = index + 1
        start = candidates[index]["start"]
        while stop < len(candidates) and candidates[stop]["start"] == start:
            stop += 1
        end = min(duration, min(w["end"] for w in candidates[index:stop]),
                  candidates[stop]["start"] if stop < len(candidates) else duration)
        if end > start:
            step = (end - start) / (stop - index)
            for offset, word in enumerate(candidates[index:stop]):
                word["start"] = start + offset * step
                word["end"] = start + (offset + 1) * step
                words.append(word)
        index = stop
    return {"schema_version": 1, "timebase": "source_seconds", "duration": duration,
            "timing": "inferred from YouTube segments; not forced-aligned or speaker-labelled",
            "cleanup": "display tags, >>, bracketed/parenthesized cues and music glyphs removed; verify speech",
            "words": words, "provenance": {"original_json3": data}}


def transcript_text(words: list[dict]) -> str:
    lines = []
    group = []
    for word in words:
        if group and (word["start"] - group[0]["start"] >= 12 or
                      word["start"] - group[-1]["end"] > 2):
            lines.append(f'[{group[0]["start"]:.3f}–{group[-1]["end"]:.3f}] ' +
                         " ".join(w["text"] for w in group))
            group = []
        group.append(word)
    if group:
        lines.append(f'[{group[0]["start"]:.3f}–{group[-1]["end"]:.3f}] ' +
                     " ".join(w["text"] for w in group))
    return "\n".join(lines) + "\n"


def pipe_blocks(command: list[str], size: int) -> Iterator[bytes]:
    """Bounded raw pipe; stderr stays small (-v error), always reap failed children."""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.stdout is not None and process.stderr is not None
    try:
        while True:
            block = bytearray()
            while len(block) < size:
                chunk = process.stdout.read(size - len(block))
                if not chunk:
                    break
                block.extend(chunk)
            if not block:
                break
            yield bytes(block)
        error = process.stderr.read().decode(errors="replace")
        if process.wait() != 0:
            raise RuntimeError(f"FFmpeg failed: {error[-4000:]}")
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdout.close()
        process.stderr.close()


def audio_scan(source: Path, duration: float) -> tuple[list[dict], dict, list[dict]]:
    command = ["ffmpeg", "-v", "error", "-xerror", "-nostdin", "-threads", "1", "-i", str(source),
               "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "pipe:1"]
    rows = []
    previous_sample = 0.0
    for index, block in enumerate(pipe_blocks(command, 4000 * 2)):
        samples = np.frombuffer(block, dtype="<i2").astype(np.float32) / 32768
        if not len(samples):
            continue
        transient = float(np.max(np.abs(np.diff(np.r_[previous_sample, samples]))))
        previous_sample = float(samples[-1])
        start = index * .5
        if start >= duration:
            break
        rows.append({"time": start, "end": min(duration, start + len(samples) / 8000),
                     "rms": float(np.sqrt(np.mean(samples ** 2))),
                     "peak": float(np.max(np.abs(samples))), "transient": transient})
    thresholds = {"rms_p90": max(.015, float(np.percentile([r["rms"] for r in rows], 90))) if rows else .015,
                  "transient_p95": max(.05, float(np.percentile([r["transient"] for r in rows], 95))) if rows else .05}
    cues = []
    for row in rows:
        kinds = []
        if row["rms"] >= thresholds["rms_p90"]:
            kinds.append("audio_energy")
        if row["transient"] >= thresholds["transient_p95"]:
            kinds.append("audio_transient")
        if kinds:
            cues.append({"time": row["time"], "kinds": kinds, "features": dict(row)})
    return rows, thresholds, cues


def frames(source: Path, start: float, end: float, interval: float,
           width: int, height: int) -> Iterator[tuple[float, np.ndarray]]:
    filters = (f"tpad=stop_mode=clone:stop_duration={interval},"
               f"fps=fps=1/{interval}:start_time=0:round=up:eof_action=pass,"
               f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
               f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2")
    count = math.ceil((end - start) / interval)
    command = ["ffmpeg", "-v", "error", "-xerror", "-nostdin", "-threads", "1", "-ss", str(start),
               "-i", str(source), "-frames:v", str(count), "-map", "0:v:0", "-an",
               "-vf", filters, "-threads", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
    emitted = 0
    for index, block in enumerate(pipe_blocks(command, width * height * 3)):
        if len(block) != width * height * 3:
            raise RuntimeError("Incomplete decoded frame")
        if index >= count:
            continue
        emitted += 1
        yield start + index * interval, np.frombuffer(block, np.uint8).reshape(height, width, 3)
    if emitted != count:
        raise RuntimeError(f"Expected {count} grid frames, decoded {emitted}; inspect source duration")


def visual_scan(source: Path, duration: float) -> tuple[list[dict], dict, list[dict]]:
    rows = []
    previous_gray = previous_hist = None
    for time, rgb in frames(source, 0, duration, 1, 320, 180):
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        hist = cv2.calcHist([rgb], [0, 1, 2], None, [8, 8, 8], [0, 256] * 3).ravel()
        hist /= max(float(hist.sum()), 1)
        rows.append({"time": time, "luma": float(gray.mean() / 255),
                     "motion_absdiff": 0.0 if previous_gray is None else
                     float(cv2.absdiff(gray, previous_gray).mean() / 255),
                     "histogram_distance": 0.0 if previous_hist is None else
                     float(np.abs(hist - previous_hist).sum() / 2)})
        previous_gray, previous_hist = gray, hist
    threshold = max(.08, float(np.percentile([r["motion_absdiff"] for r in rows], 95))) if rows else .08
    thresholds = {"histogram_cut_floor": .30, "motion_p95": threshold}
    cues = []
    for index, row in enumerate(rows):
        kinds = []
        if index and row["histogram_distance"] >= thresholds["histogram_cut_floor"]:
            kinds.append("scene_change_sample")
        if index and row["motion_absdiff"] >= threshold:
            kinds.append("motion_change_sample")
        if kinds:
            cues.append({"time": row["time"], "kinds": kinds, "sample_index": index,
                         "features": dict(row)})
    return rows, thresholds, cues


def proposal_windows(cues: list[dict], duration: float, pre: float = 4,
                     post: float = 8, minimum: float = 10, maximum: float = 35,
                     gap: float = 3) -> list[dict]:
    if duration <= 0 or not (0 < minimum <= maximum) or pre < 0 or post < 0 or gap < 0:
        raise ValueError("Invalid proposal bounds")
    ordered = sorted((c for c in cues if 0 <= c["time"] < duration), key=lambda c: c["time"])
    clusters = []
    for cue in ordered:
        if (clusters and cue["time"] - clusters[-1][-1]["time"] <= gap and
                cue["time"] - clusters[-1][0]["time"] + pre + post <= maximum):
            clusters[-1].append(cue)
        else:
            clusters.append([cue])
    windows = []
    for cluster in clusters:
        start = max(0, cluster[0]["time"] - pre)
        end = min(duration, cluster[-1]["time"] + post, start + maximum)
        if end - start < minimum:
            end = min(duration, start + minimum)
            start = max(0, end - minimum)
        if windows and start <= windows[-1]["end"] and end - windows[-1]["start"] <= maximum:
            windows[-1]["end"] = max(windows[-1]["end"], end)
            windows[-1]["cues"].extend(cluster)
        else:
            windows.append({"start": start, "end": end, "status": "needs_review", "cues": list(cluster)})
    for index, window in enumerate(windows):
        window["id"] = f"proposal-{index + 1:04d}"
    return windows


def contact_sheets(source: Path, output: Path, start: float, end: float,
                   interval: float, face_model: Path | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    detector = None
    if face_model:
        if not face_model.is_file():
            raise ValueError(f"Existing YuNet model required: {face_model}")
        detector = cv2.FaceDetectorYN.create(str(face_model), "", (480, 270), .85, .3, 5000)
    index = []
    sheets = []
    sheet = None
    draw = None
    for number, (time, rgb) in enumerate(frames(source, start, end, interval, 480, 270)):
        slot = number % 20
        if slot == 0:
            sheet = Image.new("RGB", (4 * 480, 5 * 294), "#161616")
            draw = ImageDraw.Draw(sheet)
        image = Image.fromarray(rgb)
        faces = []
        if detector is not None:
            _, detected = detector.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
            if detected is not None:
                painter = ImageDraw.Draw(image)
                for face in detected:
                    x, y, w, h = map(float, face[:4])
                    faces.append({"bbox_xywh": [x, y, w, h], "confidence": float(face[-1])})
                    painter.rectangle((x, y, x + w, y + h), outline="#00ff88", width=2)
        x, y = (slot % 4) * 480, (slot // 4) * 294
        assert sheet is not None and draw is not None
        sheet.paste(image, (x, y))
        draw.text((x + 8, y + 274), f"source {time:.3f}s | sample {number}", fill="white")
        filename = f"sheet-{number // 20 + 1:03d}.jpg"
        item = {"sample_index": number, "time": time, "sheet": filename, "slot": slot}
        if detector is not None:
            item["face_detections"] = faces
        index.append(item)
        # Save incrementally; only one sheet plus one frame is resident.
        if slot == 19:
            sheet.save(output / filename, quality=85)
            sheets.append(filename)
    if index and index[-1]["slot"] != 19:
        assert sheet is not None
        sheet.save(output / index[-1]["sheet"], quality=85)
        sheets.append(index[-1]["sheet"])
    result = {"timebase": "source_seconds", "timestamp_accuracy": "nominal resampled grid; preceding decoded frame (tail may repeat)",
              "interval": interval, "start": start, "end": end, "thumbnail_size": [480, 270],
              "grid": [4, 5], "sheets": sheets, "samples": index,
              "face_detection": "YuNet detections only; not identity or speaker attribution" if detector else "disabled"}
    save_json(output / "index.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--source", required=True, type=Path, help="Complete local video; never a partial download")
    parser.add_argument("--output", required=True, type=Path, help="Fresh output directory (or empty existing directory)")
    parser.add_argument("--captions", type=Path, help="Optional YouTube JSON3 cache; no transcription/download")
    parser.add_argument("--start", type=float, help="Review mode: bounded section start, source seconds")
    parser.add_argument("--end", type=float, help="Review mode: bounded section end, source seconds")
    parser.add_argument("--interval", type=float, help="Contact sampling interval; default 20s coarse / 1s review")
    parser.add_argument("--faces", action="store_true", help="YuNet only in review <=120s and <=240 samples")
    parser.add_argument("--face-model", type=Path, default=MODEL, help="Existing local YuNet model; never downloaded")
    args = parser.parse_args(argv)
    if not args.source.is_file():
        parser.error("source must be a completed local file")
    if not all(shutil.which(tool) for tool in ("ffmpeg", "ffprobe")):
        parser.error("ffmpeg and ffprobe must be on PATH")
    review = args.start is not None or args.end is not None
    if review and (args.start is None or args.end is None):
        parser.error("review requires both --start and --end")
    interval = args.interval if args.interval is not None else (1.0 if review else 20.0)
    if not math.isfinite(interval) or interval < .1:
        parser.error("interval must be finite and >=0.1s")
    metadata = probe(args.source)
    duration = float(metadata["format"]["duration"])
    if not math.isfinite(duration) or duration <= 0:
        parser.error("source duration must be finite and positive")
    if not any(s.get("codec_type") == "video" for s in metadata["streams"]):
        parser.error("source must have a video stream")
    if review:
        assert args.start is not None and args.end is not None
        start, end = float(args.start), float(args.end)
    else:
        start, end = 0.0, duration
    if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end <= duration):
        parser.error("require 0 <= start < end <= source duration")
    if args.faces and (not review or end - start > 120 or math.ceil((end - start) / interval) > 240):
        parser.error("faces require review <=120s and <=240 samples")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("output must be fresh/empty to avoid stale analysis artifacts")
    args.output.mkdir(parents=True, exist_ok=True)
    save_json(args.output / "metadata.json", metadata)
    manifest = {"schema_version": 1, "source": str(args.source.resolve()),
                "source_size_bytes": args.source.stat().st_size, "duration": duration,
                "mode": "targeted_review" if review else "coarse_analysis", "status": "needs_review",
                "limitations": ["Energy, motion and cuts are cues, not joke/kill/action detectors.",
                                "No virality score, semantic inference, identity, speaker ID or clip approval.",
                                "Sampled images can miss rapid events; timestamps use a nominal preceding-frame grid."],
                "complete": False}
    save_json(args.output / "manifest.json", manifest)
    if args.captions:
        normalized = normalize_json3(json.loads(args.captions.read_text()), duration)
        normalized["provenance"]["caption_path"] = str(args.captions.resolve())
        save_json(args.output / "words.json", normalized)
        (args.output / "transcript.txt").write_text(transcript_text(normalized["words"]))
    if not review:
        audio, audio_thresholds, audio_cues = (audio_scan(args.source, duration) if
            any(s.get("codec_type") == "audio" for s in metadata["streams"]) else ([], {}, []))
        save_json(args.output / "audio-features.json", {"sample_rate": 8000, "window_seconds": .5,
                  "units": "linear full-scale amplitudes", "audio_present": bool(audio),
                  "thresholds": audio_thresholds, "samples": audio, "cues": audio_cues})
        visual, visual_thresholds, visual_cues = visual_scan(args.source, duration)
        save_json(args.output / "visual-features.json", {"interval": 1, "frame_size": [320, 180],
                  "timebase": "source_seconds", "thresholds": visual_thresholds,
                  "samples": visual, "cues": visual_cues})
        cues = sorted(audio_cues + visual_cues, key=lambda cue: cue["time"])
        save_json(args.output / "scoretimes.json", {"timebase": "source_seconds", "ordering": "chronological, not quality",
                  "status": "needs_review", "cues": cues})
        save_json(args.output / "proposals.json", {"timebase": "source_seconds", "status": "needs_review",
                  "policy": {"pre_seconds": 4, "post_seconds": 8, "minimum_seconds": 10,
                             "maximum_seconds": 35, "cluster_gap_seconds": 3,
                             "overlap": "allowed when merging would exceed maximum",
                             "short_source": "may be shorter than minimum"},
                  "windows": proposal_windows(cues, duration)})
    contacts = contact_sheets(args.source, args.output / "contacts", start, end, interval,
                              args.face_model if args.faces else None)
    manifest.update({"complete": True, "contact_samples": len(contacts["samples"]),
                     "contact_sheets": len(contacts["sheets"])})
    save_json(args.output / "manifest.json", manifest)
    print(json.dumps({"output": str(args.output.resolve()), "mode": manifest["mode"],
                      "contact_samples": manifest["contact_samples"], "status": "needs_review"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
