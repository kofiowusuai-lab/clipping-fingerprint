"""Render agent-selected excerpts with SupoClip, without hosted LLM calls."""
import json
import os
import sys
import imageio_ffmpeg
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from dotenv import load_dotenv
load_dotenv(ROOT / '.env.local', override=True)
# Isolate the subtitle-capable binary to this rendering process.
bindir = ROOT / '.local/manual-render-bin'
bindir.mkdir(parents=True, exist_ok=True)
link = bindir / 'ffmpeg'
if not link.exists():
    link.symlink_to(imageio_ffmpeg.get_ffmpeg_exe())
os.environ['PATH'] = str(bindir) + os.pathsep + os.environ['PATH']
from src.video_utils import create_optimized_clip

source = ROOT / '.local/uploads/youtube-cache/K213Pn9ffIc/full.mp4'
output = ROOT / 'outputs/serhant-manual'
output.mkdir(parents=True, exist_ok=True)
words = json.loads(source.with_suffix('.transcript_cache.json').read_text())['words']
selections = [
    {'slug': '01-confidence-is-currency', 'title': 'Confidence is currency', 'start': 1542.50, 'end': 1586.65},
    {'slug': '02-best-negotiators-translate', 'title': 'The best negotiators translate', 'start': 3156.25, 'end': 3191.09},
    {'slug': '03-setbacks-not-brick-walls', 'title': 'Setbacks are not brick walls', 'start': 450.12, 'end': 488.76},
]
manifest = output / 'manifest.json'
for segment in selections:
    segment['text'] = ''.join(w['text'] for w in words if segment['start'] * 1000 <= w['start'] < segment['end'] * 1000).strip()
    segment['path'] = str(output / (segment['slug'] + '.mp4'))
    report = {}
    ok = create_optimized_clip(source, segment['start'], segment['end'], Path(segment['path']), add_subtitles=True, font_size=40, caption_template='podcast', output_format=('vertical' if segment['slug'].startswith('02-') else 'vertical_fit'), keep_ranges=[(segment['start'], segment['end'])], extend_to_sentence=False, layout_report=report)
    segment['rendered'] = ok
    segment['layout'] = report
    manifest.write_text(json.dumps(selections, indent=2))
    print(json.dumps(segment), flush=True)
    if not ok:
        raise RuntimeError('Render failed: ' + segment['slug'])
print('All manual selections rendered.', flush=True)
