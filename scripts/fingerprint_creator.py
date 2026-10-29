#!/usr/bin/env python3
"""Portable fast creator adapter: existing crop graph + atlas single words + persistent hero.

Uses creator_engine's version-1 plan (absolute paths); outputDir must not exist.
The atlas intentionally supports only single-word captions, headline and keywords,
not the full creator renderer's callouts/counters/labels. Use creator_engine.py for those.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
from creator_engine import build_graph, normalized_audio, qa, run, save, validate

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--preset', choices=['clean-energy', 'aggressive'], default='clean-energy',
                        help='Picture emphasis preset; typography uses the existing fast atlas treatment')
    args = parser.parse_args(argv)
    c = json.loads(args.plan.read_text())
    n = validate(c)
    w = Path(c['outputDir'])
    if not w.is_absolute():
        parser.error('outputDir must be absolute')
    graphics = c.get('graphics', {})
    unsupported = set(graphics) - {'headline', 'caption', 'emphasis'}
    if unsupported:
        parser.error(f'Fast atlas does not support graphics fields: {sorted(unsupported)}')
    caption = graphics.get('caption', {})
    if set(caption) - {'maxWords', 'position'} or caption.get('maxWords', 1) != 1:
        parser.error('Fast atlas requires caption.maxWords=1; only numeric position is customizable')
    emphasis = graphics.get('emphasis', {})
    if set(emphasis) - {'keywords'}:
        parser.error('Fast atlas uses its existing pop animation; only emphasis.keywords is customizable')
    headline = graphics.get('headline', '')
    if isinstance(headline, dict):
        # Explicit duration lock: atlas hero persists for the entire edited timeline.
        if set(headline) - {'text', 'start', 'end'}:
            parser.error('Fast atlas headline uses its fixed safe-area placement and sizing')
        headline = headline['text']
    w.mkdir(parents=True, exist_ok=False)
    job = {'outputDir': str(w/'graphics'), 'fontPath': c['fontPath'],
           'width': c['width'], 'height': c['height'], 'fps': c['fps'],
           'durationInFrames': n, 'words': c['words'], 'headline': headline,
           'keywords': emphasis.get('keywords', []), 'captionY': caption.get('position', .80)}
    save(w/'graphics.job.json', job)
    subprocess.run([sys.executable, str(ROOT/'scripts/creator_caption_band.py'), str(w/'graphics.job.json')], check=True)
    normalized_audio(c, w, n)
    m = json.loads((w/'graphics/manifest.json').read_text())
    if m['frameCount'] != n or m['fps'] != c['fps']:
        raise ValueError('Atlas frame/timing mismatch')
    # Reuse the existing reviewed crop/layout/zoom graph, replacing only the graphics inputs.
    graph = build_graph(c, args.preset, n).rsplit(';', 1)[0]
    graph += f';[timed][1:v]overlay=0:{m["bandTop"]}:eof_action=repeat:shortest=0:format=auto[captioned]'
    graph += ';[captioned][3:v]overlay=0:0:eof_action=repeat:shortest=0:format=auto,format=yuv420p[v]'
    (w/'filtergraph.txt').write_text(graph)
    final = w/'final.mp4'
    run(['ffmpeg', '-v', 'error', '-n', '-threads', 2, '-ss', c['start'], '-i', c['source'],
         '-framerate', c['fps'], '-start_number', m['startNumber'], '-i', m['ffmpegPattern'],
         '-i', w/'normalized.wav', '-loop', 1, '-framerate', c['fps'], '-i', m['heroPath'],
         '-filter_complex_threads', 1, '-filter_complex_script', w/'filtergraph.txt',
         '-map', '[v]', '-map', '2:a:0', '-frames:v', n, '-r', c['fps'], '-fps_mode', 'cfr',
         '-c:v', 'libx264', '-threads', 2, '-preset', 'fast', '-crf', 21, '-pix_fmt', 'yuv420p',
         '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', final])
    report = qa(c, w, n, final)
    report.update(captionMaxWords=1, persistentHero=bool(headline), renderer='existing fast Remotion atlas')
    save(w/'qa.json', report)
    (w/'post-caption.txt').write_text(c.get('postCaption', '')+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
