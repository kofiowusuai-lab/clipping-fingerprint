"""Optional local Remotion renderer for pre-edited video and second-based words.

Does not modify API/worker defaults. Run --help for the adapter contract.
"""
import argparse
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def probe(path: Path) -> dict:
    return json.loads(subprocess.run(
        ['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)],
        check=True, capture_output=True, text=True,
    ).stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', type=Path, required=True, help='Pre-edited MP4 with original audio; no burned-in captions')
    parser.add_argument('--words', type=Path, required=True, help='JSON array or {words: [...]} using clip-relative seconds, not milliseconds')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--style', choices=['clean', 'bold'], default='clean')
    parser.add_argument('--headline', default='', help='Optional truthful headline; omit for campaigns prohibiting added hooks')
    parser.add_argument('--headline-duration', type=float, default=3)
    parser.add_argument('--headline-accent', default='#ffffff', help='Six-digit hex colour for the final headline line; captions unchanged')
    parser.add_argument('--strike-word', action='append', default=[], help='Opt-in spoken-word red strike-through list (up to three words)')
    parser.add_argument('--font', type=Path, default=ROOT/'backend/fonts/Poppins-ExtraBold.ttf')
    args = parser.parse_args()
    video, output = args.video.resolve(strict=True), args.output.resolve()
    if video == output:
        parser.error('Output must not overwrite the source video')
    source = probe(video)
    v = next(s for s in source['streams'] if s['codec_type'] == 'video')
    words = json.loads(args.words.read_text())
    if isinstance(words, dict):
        words = words['words']
    fps = 30
    # Media preparation owns cuts/crops/audio. Remotion owns typography/layout.
    duration = float(v.get('duration') or source['format']['duration'])
    frames = round(duration*fps)
    if frames < 1 or not math.isfinite(duration):
        parser.error('Invalid input duration')
    output.parent.mkdir(parents=True, exist_ok=True)
    job = {
        'videoPath': str(video), 'outputPath': str(output),
        'fontPath': str(args.font.resolve(strict=True)),
        'fps': fps, 'durationInFrames': frames, 'width': int(v['width']), 'height': int(v['height']),
        'style': args.style, 'words': words, 'headline': args.headline,
        'headlineDuration': args.headline_duration, 'headlineAccent': args.headline_accent, 'strikeWords': args.strike_word,
    }
    job_path = output.with_suffix('.job.json')
    job_path.write_text(json.dumps(job, indent=2))
    subprocess.run(['node', 'render.mjs', str(job_path)], cwd=ROOT/'remotion', check=True)
    result = probe(output)
    ov = next(s for s in result['streams'] if s['codec_type'] == 'video')
    assert (int(ov['width']), int(ov['height'])) == (int(v['width']), int(v['height']))
    assert ov['codec_name'] == 'h264'
    assert abs(float(result['format']['duration'])-frames/fps) < 0.1
    if any(s['codec_type'] == 'audio' for s in source['streams']):
        oa = next(s for s in result['streams'] if s['codec_type'] == 'audio')
        assert oa['codec_name'] == 'aac'
        assert abs(float(oa['duration'])-float(ov['duration'])) < 0.1
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(output), '-f', 'null', '-'], check=True)
    report = {'path': str(output), 'duration': float(result['format']['duration']),
              'width': int(ov['width']), 'height': int(ov['height']),
              'style': args.style, 'full_decode': 'passed', 'renderer': 'remotion'}
    output.with_suffix('.verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
