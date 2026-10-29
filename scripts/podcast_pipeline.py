"""JSON-driven, manually approved local podcast edits. No services or downloads."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STAGES = ('inspect', 'transcribe', 'shortlist', 'prepare', 'render', 'qa', 'run')
RESERVED = {'videoPath', 'outputPath', 'fontPath', 'fps', 'durationInFrames', 'width', 'height', 'words', 'frameRange'}


def command(args: list[Any]) -> subprocess.CompletedProcess:
    result = subprocess.run([str(x) for x in args], capture_output=True)
    if result.returncode:
        # Do not log source URLs (which can contain credentials/query tokens).
        raise RuntimeError(f'{Path(str(args[0])).name} failed: ' + result.stderr.decode(errors='replace')[-6000:])
    return result


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temp.replace(path)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def number(value: Any, label: str, minimum: float = 0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise ValueError(f'{label} must be finite and >= {minimum}')
    return float(value)


def resolve_path(value: str, base: Path) -> Path:
    if not isinstance(value, str) or not value.strip() or '\x00' in value:
        raise ValueError('Expected a nonempty filesystem path')
    p = Path(value).expanduser()
    return (p if p.is_absolute() else base / p).resolve()


def range_frames(ranges: list, fps: int) -> list[int]:
    return [round((b - a) * fps) for a, b in ranges]


def validate_config(raw: dict, base: Path) -> dict:
    """Validate semantics and normalize paths; does not require media to exist."""
    c = json.loads(json.dumps(raw))
    if c.get('version') != 1:
        raise ValueError('version must be 1')
    if not isinstance(c.get('source'), dict) or not (c['source'].get('path') or c['source'].get('url')):
        raise ValueError('source.path or source.url is required')
    if c['source'].get('url') and not re.match(r'^https?://', c['source']['url']):
        raise ValueError('source.url must use http(s)')
    t = c.get('transcript', {})
    if t.get('units') not in ('seconds', 'milliseconds'):
        raise ValueError('transcript.units must explicitly be seconds or milliseconds')
    for section, key in ((c['source'], 'path'), (t, 'path'), (c, 'fontPath'), (c, 'outputDir')):
        if key in section:
            section[key] = str(resolve_path(section[key], base))
        elif section is not c['source']:
            raise ValueError(f'{key} is required')
    for key, default in (('width', 1080), ('height', 1920), ('fps', 30)):
        c.setdefault(key, default)
        if type(c[key]) is not int or c[key] <= 0:
            raise ValueError(f'{key} must be a positive integer')
    if c['width'] % 2 or c['height'] % 2:
        raise ValueError('width and height must be even')
    c.setdefault('crf', 19)
    if c['crf'] not in (18, 19):
        raise ValueError('Prepared footage crf must be 18 or 19')
    clips = c.get('clips')
    if not isinstance(clips, list) or not clips:
        raise ValueError('clips must be a nonempty list (manual editorial shortlist)')
    ids = set()
    for clip in clips:
        cid = clip.get('id', '')
        if not isinstance(cid, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', cid) or cid in ids:
            raise ValueError('clip ids must be unique safe slugs')
        ids.add(cid)
        ranges = clip.get('ranges', [])
        if not isinstance(ranges, list) or not ranges:
            raise ValueError(f'{cid}: nonempty source ranges required (seconds)')
        for pair in ranges:
            if not isinstance(pair, list) or len(pair) != 2:
                raise ValueError('ranges must contain [start,end] pairs')
            a, b = [number(v, 'range time') for v in pair]
            if b <= a or round((b-a)*c['fps']) < 1:
                raise ValueError('range must contain at least one frame')
        for key in ('sourceNotes', 'payoff', 'postCaption', 'headline'):
            if not isinstance(clip.get(key), str):
                raise ValueError(f'{cid}: {key} string is required')
        if not isinstance(clip.get('approval', {}), dict):
            raise ValueError('approval must be an object')
        if clip.get('approval', {}).get('approved') is True and not all(clip['approval'].get(k) for k in ('reviewer', 'reviewedAt')):
            raise ValueError('Approved edits require reviewer and reviewedAt')
        captions = clip.setdefault('captions', {'style': 'bold'})
        if not isinstance(captions, dict) or captions.get('style', 'bold') not in ('clean', 'bold'):
            raise ValueError('captions.style must be clean or bold')
        for opts in (c.get('renderOptions', {}), clip.get('renderOptions', {})):
            if not isinstance(opts, dict) or RESERVED.intersection(opts):
                raise ValueError('renderOptions must be an object and cannot replace pipeline-owned fields')
        if not isinstance(clip.get('graphics', {}), dict):
            raise ValueError('graphics is editorial metadata; use renderOptions for supported JS props')
        shots = clip.get('shots', [])
        if not isinstance(shots, list):
            raise ValueError('shots must be an array')
        for ri, (a, b) in enumerate(ranges):
            selected = [s for s in shots if s.get('rangeIndex') == ri]
            if shots and not selected:
                raise ValueError('Supplied shots must partition every range')
            cursor = a
            for shot in selected:
                start = number(shot.get('start'), 'shot start')
                end = number(shot.get('end'), 'shot end')
                if abs(start-cursor) > 1e-6 or end <= start or end > b+1e-6:
                    raise ValueError('shots must exactly partition each range in array order')
                if round((end-a)*c['fps']) <= round((start-a)*c['fps']):
                    raise ValueError('shot is shorter than one timeline frame')
                if 'videoEnd' in shot:
                    video_end = number(shot['videoEnd'], 'shot videoEnd')
                    if not start < video_end <= end or shot.get('reviewed') is not True:
                        raise ValueError('videoEnd must be inside the shot with reviewed=true; audio continues to end')
                    if round((video_end-start)*c['fps']) < 1:
                        raise ValueError('videoEnd must retain at least one source frame')
                if shot.get('reaction', False) and end-start < 3:
                    raise ValueError('Reaction shots must hold at least 3 seconds')
                if shot.get('mode', 'auto') not in ('auto', 'contain', 'crop'):
                    raise ValueError('shot mode must be auto, contain or crop')
                if shot.get('mode') == 'crop':
                    if shot.get('reviewed') is not True:
                        raise ValueError('Manual crop plans require reviewed=true')
                    box = shot.get('crop', {})
                    for key in ('x', 'y', 'width', 'height'):
                        number(box.get(key), f'crop.{key}', 2 if key in ('width', 'height') else 0)
                    track = shot.get('track', [])
                    last = -1.0
                    for point in track:
                        time = number(point.get('time'), 'track time')
                        if time <= last or time > end-start:
                            raise ValueError('track times must increase within shot (relative seconds)')
                        last = time
                        number(point.get('x'), 'track x')
                        number(point.get('y'), 'track y')
                cursor = end
            if selected and abs(cursor-b) > 1e-6:
                raise ValueError('shots must cover the entire range')
        if any(type(s.get('rangeIndex')) is not int or not 0 <= s['rangeIndex'] < len(ranges) for s in shots):
            raise ValueError('shot.rangeIndex is invalid')
        riser = clip.get('riser')
        if riser:
            riser['path'] = str(resolve_path(riser['path'], base))
            cut = number(riser.get('cutSeconds'), 'riser cutSeconds')
            crest = number(riser.get('crestSeconds'), 'riser crestSeconds', .001)
            boundaries = []
            total = 0
            for n in range_frames(ranges, c['fps']):
                total += n/c['fps']
                boundaries.append(total)
            if cut < crest or not any(abs(cut-x) <= 1/c['fps'] for x in boundaries[:-1]):
                raise ValueError('Riser must crest at a completed range boundary with room for the swell')
            if not riser.get('semanticNote'):
                raise ValueError('riser.semanticNote is required')
            number(riser.get('gain', .28), 'riser gain')
    inputs = [c['source'].get('path'), t['path'], c['fontPath']] + [x.get('riser', {}).get('path') for x in clips] + optional_assets(c)
    out = Path(c['outputDir'])
    if any(p and (out == Path(p) or out in Path(p).parents) for p in inputs):
        raise ValueError('outputDir must not contain or overwrite an input')
    protected = [p for p in [c['source'].get('path'), c['fontPath'], *[x.get('riser', {}).get('path') for x in clips], *optional_assets(c)] if p]
    if any(same_file(Path(t['path']), Path(p)) for p in protected):
        raise ValueError('Transcript target must not alias a source/font/riser input')
    return c


def same_file(a: Path, b: Path) -> bool:
    if a.resolve() == b.resolve():
        return True
    try:
        return a.samefile(b)
    except OSError:
        return False


def optional_assets(c: dict) -> list[str]:
    assets = []
    for opts in [c.get('renderOptions', {}), *(clip.get('renderOptions', {}) for clip in c['clips'])]:
        values = [opts.get('supportingVideo', {}).get('videoPath'), opts.get('endcard', {}).get('imagePath')]
        values += [x.get('imagePath') for x in opts.get('overlays', [])]
        assets.extend(str(Path(x).resolve()) for x in values if x)
    return sorted(set(assets))


def load_config(path: Path) -> dict:
    return validate_config(json.loads(path.read_text()), path.resolve().parent)


def remap_words(words: list[dict], ranges: list, fps: int, units: str) -> list[dict]:
    if units not in ('seconds', 'milliseconds'):
        raise ValueError('Explicit transcript units required')
    scale = 1000 if units == 'milliseconds' else 1
    clean = []
    previous = -1.0
    for w in words:
        a = number(w.get('start'), 'word start') / scale
        b = number(w.get('end'), 'word end') / scale
        text = re.sub(r'>>\s*', '', str(w.get('text', ''))).strip()
        if b <= a or a < previous-0.001:
            raise ValueError('Transcript words must be ordered and nonoverlapping; correct the cache manually')
        previous = b
        if text and not re.fullmatch(r'\[[^]]+\]', text):
            clean.append((text, a, b))
    result = []
    offset = 0.0
    for (a, b), frames in zip(ranges, range_frames(ranges, fps)):
        duration = frames / fps
        for text, start, end in clean:
            if a <= start < b:
                x, y = offset+start-a, offset+min(end-a, duration)
                if y > x:
                    result.append({'text': text, 'start': round(x, 6), 'end': round(y, 6)})
        offset += duration
    return result


def probe(path: Path) -> dict:
    return json.loads(command(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', path]).stdout)


def decode(path: Path) -> None:
    command(['ffmpeg', '-v', 'error', '-xerror', '-i', path, '-f', 'null', '-'])


def video_check(path: Path, c: dict, frames: int, audio: bool = False) -> dict:
    p = probe(path)
    v = next(s for s in p['streams'] if s['codec_type'] == 'video')
    duration = frames / c['fps']
    from fractions import Fraction
    if (v['width'], v['height']) != (c['width'], c['height']) or abs(float(Fraction(v['avg_frame_rate']))-c['fps']) > .001:
        raise ValueError('Unexpected video dimensions/fps')
    if abs(float(v.get('duration', p['format']['duration']))-duration) > 1/c['fps']+.01:
        raise ValueError('Unexpected video duration')
    if v.get('nb_frames') and int(v['nb_frames']) != frames:
        raise ValueError('Unexpected frame count')
    if audio:
        a = next(s for s in p['streams'] if s['codec_type'] == 'audio')
        if abs(float(a.get('duration', p['format']['duration']))-duration) > .08:
            raise ValueError('Unexpected audio duration')
    decode(path)
    return p


def interpolation(points: list[dict], key: str) -> str:
    expression = f'{points[-1][key]:.5f}'
    for left, right in reversed(list(zip(points, points[1:]))):
        t, nt = left['time'], right['time']
        expression = f"if(lt(t,{nt:.6f}),{left[key]:.5f}+({right[key]-left[key]:.5f})*clip((t-{t:.6f})/{nt-t:.6f},0,1),{expression})"
    return expression


def crop_filter(shot: dict, sw: int, sh: int, width: int, height: int) -> str:
    box = shot['crop']
    w, h = int(box['width'])//2*2, int(box['height'])//2*2
    points = shot.get('track') or [{'time': 0, 'x': box['x'], 'y': box['y']}]
    if w > sw or h > sh or any(p['x']+w > sw or p['y']+h > sh for p in points):
        raise ValueError('Crop extends outside the source frame')
    return f"crop={w}:{h}:x='{interpolation(points, 'x')}':y='{interpolation(points, 'y')}',scale={width}:{height}:flags=lanczos,setsar=1"


def automatic_plan(source: Path, shot: dict, sw: int, sh: int, aspect: float) -> dict:
    """Sample every <=1s. Exactly one face at EVERY sample, else safe contain.

    This is face tracking, never active-speaker identification. The caller must
    supply source camera-shot boundaries; automatic camera detection is absent.
    """
    try:
        import cv2
        import numpy as np
        sys.path.insert(0, str(ROOT/'backend'))
        from src.media.face_detection import YuNetFaceDetector
        detector = YuNetFaceDetector()  # existing bundled model only
    except Exception:
        return {'mode': 'contain', 'reason': 'YuNet unavailable; no model downloaded'}
    capture = cv2.VideoCapture(str(source))
    a, b = shot['start'], shot.get('videoEnd', shot['end'])
    samples = []
    reason = None
    try:
        for t in np.linspace(a, max(a, b-.05), max(2, math.ceil(b-a)+1)):
            capture.set(cv2.CAP_PROP_POS_MSEC, float(t)*1000)
            ok, frame = capture.read()
            faces = detector.detect(frame) if ok else []
            if len(faces) != 1:
                reason = 'Missing/ambiguous face or unreadable sample; whole shot contained'
                break
            samples.append((float(t-a), faces[0]))
    finally:
        capture.release()
    if reason:
        return {'mode': 'contain', 'reason': reason}
    face_height = float(np.median([f[3] for _, f in samples]))
    h = min(sh, sw/aspect, max(sh*.6, face_height*3))
    h = int(h)//2*2
    w = int(h*aspect)//2*2
    points = []
    for i, (t, face) in enumerate(samples):
        neighbors = samples[max(0, i-1):i+2]
        x = float(np.mean([f[0]+f[2]/2-w/2 for _, f in neighbors]))
        y = float(np.mean([f[1]-.4*f[3] for _, f in neighbors]))
        points.append({'time': t, 'x': max(0, min(sw-w, x)), 'y': max(0, min(sh-h, y))})
    # If smoothing would cut even one sampled face/hair, retain the whole frame.
    for point, (_, face) in zip(points, samples):
        x, y, fw, fh = face[:4]
        if x < point['x'] or x+fw > point['x']+w or y-.15*fh < point['y'] or y+fh > point['y']+h:
            return {'mode': 'contain', 'reason': 'Face safety margin did not fit smoothed track'}
    return {'mode': 'crop', 'crop': {'x': points[0]['x'], 'y': points[0]['y'], 'width': w, 'height': h}, 'track': points, 'reason': 'Single-face samples, smoothed; not speaker ID'}


def fingerprint(c: dict) -> str:
    inputs = [c['source'].get('path'), c['transcript']['path'], c['fontPath']]
    inputs += [x.get('riser', {}).get('path') for x in c['clips']]
    inputs += optional_assets(c)
    metadata = []
    for value in inputs:
        if value:
            path = Path(value)
            st = path.stat()
            # Full source hashing is intentionally avoided for multi-hour media.
            metadata.append((str(path), st.st_size, st.st_mtime_ns))
    code = [Path(__file__), ROOT/'remotion/render.mjs', ROOT/'remotion/schema.mjs']
    code += sorted((ROOT/'remotion/src').glob('**/*'))
    hashes = [(str(p), digest(p)) for p in code if p.is_file()]
    return hashlib.sha256(json.dumps([c, metadata, hashes], sort_keys=True).encode()).hexdigest()


def receipt_valid(work: Path, stage: str, key: str) -> bool:
    try:
        data = json.loads((work/f'{stage}.receipt.json').read_text())
        if data['fingerprint'] != key:
            return False
        for name, checksum in data['outputs'].items():
            p = work/name
            if digest(p) != checksum:
                return False
            if p.suffix in ('.mp4', '.wav'):
                decode(p)
        return True
    except (OSError, ValueError, KeyError, RuntimeError):
        return False


def save_receipt(work: Path, stage: str, key: str, paths: list[Path]) -> None:
    dump(work/f'{stage}.receipt.json', {'fingerprint': key, 'outputs': {str(p.relative_to(work)): digest(p) for p in paths}})


def dependency_key(key: str, work: Path, stage: str) -> str:
    receipt = work/f'{stage}.receipt.json'
    if not receipt.exists():
        raise ValueError(f'Run {stage} first')
    return hashlib.sha256((key+digest(receipt)).encode()).hexdigest()


def require_approval(clip: dict) -> None:
    if clip.get('approval', {}).get('approved') is not True:
        raise ValueError(f"{clip['id']}: manual editorial approval required; review shortlist then edit the config")


def prepare(c: dict, clip: dict, work: Path) -> list[Path]:
    import numpy as np
    source = Path(c['source']['path'])
    p = probe(source)
    v = next(s for s in p['streams'] if s['codec_type'] == 'video')
    sw, sh = v['width'], v['height']
    source_duration = float(p['format']['duration'])
    if any(b > source_duration+.01 for _, b in clip['ranges']):
        raise ValueError('Edit range exceeds source duration')
    fps, width, height = c['fps'], c['width'], c['height']
    frames = range_frames(clip['ranges'], fps)
    transcript = json.loads(Path(c['transcript']['path']).read_text())
    words = remap_words(transcript['words'] if isinstance(transcript, dict) else transcript, clip['ranges'], fps, c['transcript']['units'])
    dump(work/'words.json', words)
    plans, parts, pcm = [], [], []
    for ri, ((a, b), count) in enumerate(zip(clip['ranges'], frames)):
        shots = [s for s in clip.get('shots', []) if s['rangeIndex'] == ri] or [{'start': a, 'end': b, 'mode': 'auto', 'rangeIndex': ri}]
        for shot in shots:
            plan = dict(shot)
            if shot.get('mode', 'auto') == 'auto':
                plan.update(automatic_plan(source, shot, sw, sh, width/height))
            n = round((shot['end']-a)*fps)-round((shot['start']-a)*fps)
            part = work/f'part-{len(parts):03d}.mp4'
            if plan['mode'] == 'crop':
                vf = crop_filter(plan, sw, sh, width, height)
            else:
                vf = f'scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1'
            hold = shot['end']-shot.get('videoEnd', shot['end'])
            vf += f',fps={fps}'
            if hold:
                safe_frames = max(1, math.floor((shot['videoEnd']-shot['start'])*fps+1e-6))
                vf += f',trim=end_frame={safe_frames}'
            vf += f',tpad=stop_mode=clone:stop_duration={hold+.1}'
            command(['ffmpeg', '-v', 'error', '-y', '-ss', shot['start'], '-i', source, '-an', '-vf', vf, '-frames:v', n, '-c:v', 'libx264', '-preset', 'fast', '-crf', c['crf'], '-pix_fmt', 'yuv420p', part])
            parts.append(part)
            plans.append({**plan, 'frames': n, 'tailHold': hold})
        raw = command(['ffmpeg', '-v', 'error', '-ss', a, '-i', source, '-t', b-a, '-vn', '-ar', '48000', '-ac', '2', '-f', 'f32le', 'pipe:1']).stdout
        piece = np.frombuffer(raw, dtype='<f4').reshape(-1, 2).copy()
        target = round(count/fps*48000)
        piece = np.pad(piece, ((0, max(0, target-len(piece))), (0, 0)))[:target]
        pcm.append(piece)
    listing = work/'concat.txt'
    # Relative generated names avoid FFmpeg concat quoting problems in user paths.
    listing.write_text('\n'.join(f"file '{part.name}'" for part in parts)+'\n')
    picture = work/'picture.mp4'
    command(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', listing, '-c', 'copy', '-movflags', '+faststart', picture])
    video_check(picture, c, sum(frames))
    speech = np.concatenate(pcm)
    riser = clip.get('riser')
    if riser:
        raw = command(['ffmpeg', '-v', 'error', '-i', riser['path'], '-ar', '48000', '-ac', '2', '-f', 'f32le', 'pipe:1']).stdout
        swell = np.frombuffer(raw, dtype='<f4').reshape(-1, 2).copy()
        crest, cut = round(riser['crestSeconds']*48000), round(riser['cutSeconds']*48000)
        if crest > len(swell) or cut > len(speech):
            raise ValueError('Riser crest/cut exceeds supplied media')
        swell = swell[:crest]
        fade = min(48, crest)
        swell[-fade:] *= np.linspace(1, 0, fade)[:, None]
        speech[cut-crest:cut] += swell*riser.get('gain', .28)
    raw_path = work/'mix.f32'
    speech.astype('<f4').tofile(raw_path)
    mix = work/'mix.wav'
    command(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', '48000', '-ac', '2', '-i', raw_path, '-c:a', 'pcm_f32le', mix])
    raw_path.unlink()
    norm = 'loudnorm=I=-16:TP=-1.5:LRA=11'
    first = command(['ffmpeg', '-hide_banner', '-i', mix, '-af', norm+':print_format=json', '-f', 'null', '-']).stderr.decode()
    measured = json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}', first, re.S)[-1])
    if not all(math.isfinite(float(measured[k])) for k in ('input_i', 'input_tp', 'input_lra', 'input_thresh', 'target_offset')):
        raise ValueError('Cannot normalize silent/nonfinite audio')
    second = norm + ''.join(f':{dest}={measured[src]}' for dest, src in [('measured_I', 'input_i'), ('measured_TP', 'input_tp'), ('measured_LRA', 'input_lra'), ('measured_thresh', 'input_thresh'), ('offset', 'target_offset')]) + ':linear=true:print_format=json'
    normalized = work/'normalized.wav'
    second_log = command(['ffmpeg', '-hide_banner', '-y', '-i', mix, '-af', second, '-ar', '48000', '-c:a', 'pcm_s24le', normalized]).stderr.decode()
    decode(normalized)
    actual = json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}', second_log, re.S)[-1])
    dump(work/'prepare.json', {'shots': plans, 'frames': sum(frames), 'duration': sum(frames)/fps, 'rangeFrames': frames, 'loudnormPass1': measured, 'loudnormPass2': actual, 'visualReview': 'pending', 'limitations': 'Face detection is not speaker ID; sample tracking requires visual review and supplied camera boundaries.'})
    for part in parts:
        part.unlink()  # retain high-quality joined picture, not duplicate encodes
    listing.unlink()
    return [picture, mix, normalized, work/'words.json', work/'prepare.json']


def render(c: dict, clip: dict, work: Path) -> list[Path]:
    info = json.loads((work/'prepare.json').read_text())
    job = {'videoPath': str((work/'picture.mp4').resolve()), 'outputPath': str((work/'graphics.mp4').resolve()), 'fontPath': c['fontPath'], 'fps': c['fps'], 'durationInFrames': info['frames'], 'width': c['width'], 'height': c['height'], 'style': clip.get('captions', {}).get('style', 'bold'), 'words': json.loads((work/'words.json').read_text()), 'headline': clip['headline'], 'headlineDuration': clip.get('captions', {}).get('headlineDuration', 3), 'headlineAccent': clip.get('captions', {}).get('headlineAccent', '#ffffff'), 'strikeWords': clip.get('captions', {}).get('strikeWords', [])}
    job.update(c.get('renderOptions', {}))
    job.update(clip.get('renderOptions', {}))
    dump(work/'render.job.json', job)
    # JS validates optional graphics props. No guessed API additions here.
    command(['node', ROOT/'remotion/render.mjs', work/'render.job.json'])
    video_check(work/'graphics.mp4', c, info['frames'])
    final = work/'final.mp4'
    command(['ffmpeg', '-v', 'error', '-y', '-i', work/'graphics.mp4', '-i', work/'normalized.wav', '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', final])
    video_check(final, c, info['frames'], audio=True)
    (work/'post-caption.txt').write_text(clip['postCaption']+'\n')
    return [work/'render.job.json', work/'graphics.mp4', final, work/'post-caption.txt']


def qa_times(duration: float, boundaries: list[float], fps: int) -> list[float]:
    times = [0, duration*.25, duration*.5, duration*.75, duration-1/fps]
    for cut in boundaries:
        times.extend([cut-1/fps, cut, cut+1/fps, cut+.2])
    return sorted({round(max(0, min(duration-1/fps, t)), 6) for t in times})


def qa(c: dict, clip: dict, work: Path) -> list[Path]:
    import numpy as np
    from PIL import Image, ImageDraw
    info = json.loads((work/'prepare.json').read_text())
    final = work/'final.mp4'
    p = video_check(final, c, info['frames'], audio=True)
    raw = command(['ffmpeg', '-v', 'error', '-i', final, '-vn', '-ar', '48000', '-ac', '2', '-f', 'f32le', 'pipe:1']).stdout
    audio = np.frombuffer(raw, dtype='<f4').astype('float64')
    rms, peak = float(np.sqrt(np.mean(audio**2))), float(np.max(np.abs(audio)))
    logs = command(['ffmpeg', '-hide_banner', '-i', final, '-af', 'silencedetect=noise=-45dB:d=0.5', '-vf', 'blackdetect=d=0.1:pix_th=0.1:pic_th=0.98', '-f', 'null', '-']).stderr.decode(errors='replace')
    events = [line.strip() for line in logs.splitlines() if re.search(r'(black_start:|silence_start:|silence_end:)', line)]
    cuts, total = [], 0
    for n in info['rangeFrames'][:-1]:
        total += n/c['fps']
        cuts.append(total)
    offset = 0
    for ri, count in enumerate(info['rangeFrames']):
        for shot in info['shots']:
            if shot.get('rangeIndex') == ri and shot['start'] > clip['ranges'][ri][0]+1e-6:
                cuts.append(offset+round((shot['start']-clip['ranges'][ri][0])*c['fps'])/c['fps'])
        offset += count/c['fps']
    times = qa_times(info['duration'], cuts, c['fps'])
    thumb_width = 216
    thumb_height = round(thumb_width*c['height']/c['width'])
    sheet = Image.new('RGB', (thumb_width*4, (thumb_height+24)*math.ceil(len(times)/4)), '#151515')
    draw = ImageDraw.Draw(sheet)
    import io
    for i, t in enumerate(times):
        raw = command(['ffmpeg', '-v', 'error', '-ss', t, '-i', final, '-frames:v', '1', '-vf', f'scale={thumb_width}:{thumb_height}', '-f', 'image2pipe', '-vcodec', 'png', 'pipe:1']).stdout
        image = Image.open(io.BytesIO(raw))
        x, y = i % 4*thumb_width, i//4*(thumb_height+24)
        sheet.paste(image, (x, y+24))
        draw.text((x+5, y+5), f'{t:.3f}s', fill='white')
    sheet.save(work/'contact-sheet.jpg')
    # Existing all-frame central-band regression check catches known Remotion
    # strip corruption that decode alone cannot. Effects require reviewed masks.
    checker = ROOT/'scripts/check_remotion_frames.py'
    comparison = {'status': 'not_run', 'reason': 'Run the all-frame checker with reviewed effect exclusions before delivery'}
    report = {'path': str(final), 'ffprobe': p, 'fullDecode': 'passed', 'audio': {'rms': rms, 'peak': peak, 'rmsDbfs': 20*math.log10(max(rms, 1e-12)), 'peakDbfs': 20*math.log10(max(peak, 1e-12))}, 'blackSilenceEvents': events, 'contactSheet': str(work/'contact-sheet.jpg'), 'timestamps': times, 'cuts': sorted(set(cuts)), 'visualReview': 'pending', 'allFramePictureComparison': comparison, 'deliveryReady': False, 'reviewRequired': ['Watch/listen for word onsets, correct speaker, source cards, framing and captions', 'Inspect cuts, end and all effect frames', f'Run {checker.name} with appropriate reviewed masks; no inferred visual pass']}
    dump(work/'qa.json', report)
    return [work/'qa.json', work/'contact-sheet.jpg']


def transcribe(c: dict, model_path: Path, start: float, end: float | None, force: bool) -> None:
    """Explicit local Whisper checkpoint only; never resolve/download a model name."""
    import tempfile
    import whisper
    model_path = model_path.expanduser().resolve(strict=True)
    if not model_path.is_file() or model_path.suffix != '.pt':
        raise ValueError('--model-path must be an existing trusted local .pt Whisper checkpoint')
    target = Path(c['transcript']['path'])
    protected = [model_path, Path(c['source']['path']), Path(c['fontPath'])] + [Path(x['riser']['path']) for x in c['clips'] if x.get('riser')] + [Path(x) for x in optional_assets(c)]
    if any(same_file(target, item) for item in protected):
        raise ValueError('Transcript target must not overwrite any input/checkpoint')
    if target.exists() and not force:
        raise ValueError('Transcript cache exists; reuse it or explicitly pass --force-transcript')
    source = Path(c['source']['path']).resolve(strict=True)
    number(start, 'transcribe start')
    if end is not None and number(end, 'transcribe end') <= start:
        raise ValueError('transcribe end must exceed start')
    with tempfile.TemporaryDirectory(prefix='podcast-whisper-') as temp:
        wav = Path(temp)/'speech.wav'
        cmd = ['ffmpeg', '-v', 'error', '-y', '-ss', start, '-i', source]
        if end is not None:
            cmd += ['-t', end-start]
        command(cmd+['-vn', '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', wav])
        model = whisper.load_model(str(model_path), device='cpu')
        result = model.transcribe(str(wav), word_timestamps=True, fp16=False, verbose=False)
    scale = 1000 if c['transcript']['units'] == 'milliseconds' else 1
    words = [{'text': w['word'].strip(), 'start': round((start+w['start'])*scale, 6), 'end': round((start+w['end'])*scale, 6), 'speaker': None}
             for segment in result['segments'] for w in segment.get('words', []) if w['word'].strip() and w['end'] > w['start']]
    dump(target, {'words': words, 'units': c['transcript']['units'], 'engine': 'local-whisper', 'model': model_path.name, 'sourceOffsetSeconds': start, 'review': 'ASR only; no speaker identity; verify words and edit handles against source'})


def inspect(c: dict, clips: list[dict]) -> dict:
    report = {'version': 1, 'sourceAvailable': False, 'selection': [x['id'] for x in clips], 'manualEditorialRequired': True, 'visualReview': 'pending'}
    if c['source'].get('path') and Path(c['source']['path']).is_file():
        report['sourceAvailable'] = True
        report['ffprobe'] = probe(Path(c['source']['path']))
    else:
        report['sourceNote'] = 'URL is provenance only. Acquire source separately and set source.path; no downloader/services invoked.'
    report['transcriptAvailable'] = Path(c['transcript']['path']).is_file()
    report['fontAvailable'] = Path(c['fontPath']).is_file()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=STAGES)
    parser.add_argument('--config', type=Path, required=True, help='Version-1 editorial JSON; paths relative to this file')
    parser.add_argument('--only', action='append', default=[], help='Clip id (repeat or comma-separate)')
    parser.add_argument('--resume', action='store_true', help='Reuse only checksum-matched receipts and decodable media')
    parser.add_argument('--model-path', type=Path, help='transcribe only: existing trusted local Whisper .pt; never downloads')
    parser.add_argument('--transcribe-start', type=float, default=0, help='Source seconds; output words retain source timestamps')
    parser.add_argument('--transcribe-end', type=float, help='Optional source end seconds (limit work/memory)')
    parser.add_argument('--force-transcript', action='store_true', help='Explicitly replace an existing transcript cache')
    args = parser.parse_args(argv)
    try:
        c = load_config(args.config)
        ids = {x for item in args.only for x in item.split(',') if x}
        known = {x['id'] for x in c['clips']}
        if ids-known:
            raise ValueError('Unknown --only clip ids: '+', '.join(sorted(ids-known)))
        clips = [x for x in c['clips'] if not ids or x['id'] in ids]
        out = Path(c['outputDir'])
        out.mkdir(parents=True, exist_ok=True)
        if args.stage in ('inspect', 'run'):
            report = inspect(c, clips)
            dump(out/'inspect.json', report)
            print(json.dumps({k: v for k, v in report.items() if k != 'ffprobe'}))
        if args.stage in ('shortlist', 'run'):
            # Never auto-approve or auto-select. Preserve the supplied evidence.
            dump(out/'shortlist.json', {'version': 1, 'selectionMethod': 'manual editorial JSON; no automatic highlighter', 'clips': clips, 'instructions': 'Review source, complete hook/pacing/payoff, shots and word handles. Set approval.approved, reviewer, reviewedAt in the input config.'})
        if args.stage in ('inspect', 'shortlist'):
            return 0
        if not c['source'].get('path'):
            raise ValueError('Processing requires source.path; URL alone is provenance, not a download instruction')
        if args.stage == 'transcribe':
            if args.model_path is None:
                raise ValueError('transcribe requires --model-path to an existing local checkpoint')
            transcribe(c, args.model_path, args.transcribe_start, args.transcribe_end, args.force_transcript)
            print('Transcript cache written; ASR requires source review, not editorial approval')
            return 0
        key = fingerprint(c)
        for clip in clips:
            require_approval(clip)
            work = out/clip['id']
            work.mkdir(parents=True, exist_ok=True)
            stages = ('prepare', 'render', 'qa') if args.stage == 'run' else (args.stage,)
            for stage in stages:
                stage_key = key
                if stage in ('render', 'qa'):
                    if not receipt_valid(work, 'prepare', key):
                        raise ValueError('Prepared outputs missing/stale/corrupt; run prepare --resume first')
                    stage_key = dependency_key(key, work, 'prepare')
                if stage == 'qa':
                    if not receipt_valid(work, 'render', stage_key):
                        raise ValueError('Rendered outputs missing/stale/corrupt; run render --resume first')
                    stage_key = dependency_key(stage_key, work, 'render')
                if args.resume and receipt_valid(work, stage, stage_key):
                    print(f"{clip['id']}: {stage} reused (checksums + full decode verified)")
                    continue
                # A killed/failed attempt can never leave a valid completion receipt.
                (work/f'{stage}.receipt.json').unlink(missing_ok=True)
                outputs = globals()[stage](c, clip, work)
                save_receipt(work, stage, stage_key, outputs)
                print(f"{clip['id']}: {stage} completed; visual review pending")
        return 0
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, StopIteration) as exc:
        print(f'podcast-pipeline: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
