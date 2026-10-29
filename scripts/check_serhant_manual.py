"""Probe, decode and build opening/middle/closing review sheets."""
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1] / 'outputs/serhant-manual'
manifest = json.loads((root / 'manifest.json').read_text())
reports = []
for segment in manifest:
    path = Path(segment['path'])
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    probe = json.loads(result.stdout)
    video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    duration = float(probe['format']['duration'])
    assert (video['width'], video['height']) == (1080, 1920)
    assert abs(duration - (segment['end'] - segment['start'])) < 0.5
    decode = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'null', '-'], capture_output=True, text=True, check=True)
    assert not decode.stderr.strip(), decode.stderr
    sheet = Image.new('RGB', (360 * 4, 680), '#161616')
    draw = ImageDraw.Draw(sheet)
    for i, t in enumerate([0.5, 4.0, duration / 2, duration - 0.5]):
        imagepath = root / f"{segment['slug']}-frame-{i}.jpg"
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', str(path), '-frames:v', '1', '-vf', 'scale=360:640', str(imagepath)], check=True)
        sheet.paste(Image.open(imagepath), (i * 360, 30))
        draw.text((i * 360 + 12, 8), f'{t:.2f}s', fill='white')
    sheet.save(root / f"{segment['slug']}-review.jpg")
    reports.append({'path': str(path), 'duration': duration, 'width': video['width'], 'height': video['height'], 'video_codec': video['codec_name'], 'audio_codec': audio['codec_name'], 'bytes': path.stat().st_size, 'full_decode': 'passed'})
(root / 'verification.json').write_text(json.dumps(reports, indent=2))
assert len(reports) == 3
print(json.dumps(reports, indent=2))
