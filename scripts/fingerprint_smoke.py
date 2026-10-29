#!/usr/bin/env python3
"""Native/container entrypoint and REAL synthetic render smoke; no network/model downloads.

python scripts/fingerprint_smoke.py smoke --output-dir /absolute/fresh-dir [--font FONT.ttf]
Other commands forward remaining arguments unchanged to existing local CLIs:
creator (fast atlas adapter), creator-engine, creator-graphics, creator-atlas,
caption-band, podcast, remotion. Use COMMAND --help for its own options.
This tests technical rendering, NOT real speech sync, editorial QC or AI edit reproducibility.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = {
    'creator': ('python', 'scripts/fingerprint_creator.py'),
    'creator-engine': ('python', 'scripts/creator_engine.py'),
    'creator-batch': ('python', 'scripts/render_ddg_batch_clip.py'),
    'podcast-captions': ('python', 'scripts/render_with_remotion.py'),
    'creator-graphics': ('node', 'remotion/render-creator.mjs'),
    'creator-atlas': ('node', 'remotion/render-creator-atlas.mjs'),
    'caption-band': ('python', 'scripts/creator_caption_band.py'),
    'podcast': ('python', 'scripts/podcast_pipeline.py'),
    'remotion': ('node', 'remotion/render.mjs'),
}


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in COMMANDS:
        runtime, script = COMMANDS[sys.argv[1]]
        return subprocess.call([sys.executable if runtime == 'python' else runtime,
                                str(ROOT/script), *sys.argv[2:]])
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['smoke'])
    parser.add_argument('--output-dir', type=Path, required=True, help='Fresh directory; retained on success/failure')
    parser.add_argument('--font', type=Path, default=Path(os.environ.get('FINGERPRINT_FONT', str(ROOT/'backend/fonts/Poppins-ExtraBold.ttf'))))
    args = parser.parse_args()
    for tool in ['ffmpeg', 'ffprobe', 'node']:
        if not shutil.which(tool):
            parser.error(f'{tool} is not on PATH')
    font = args.font.expanduser().resolve(strict=True)
    if font.suffix.lower() != '.ttf':
        parser.error('The creator atlas needs an actual local TrueType .ttf font')
    out = args.output_dir.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=False)
    logdir = out/'logs'
    logdir.mkdir()
    calls = []

    def run(cmd):
        cmd = [str(x) for x in cmd]
        calls.append(cmd)
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True)
        (logdir/f'{len(calls):02d}.log').write_bytes(result.stdout+b'\n--- STDERR ---\n'+result.stderr)
        if result.returncode:
            raise RuntimeError(f'Command failed ({result.returncode}): {cmd[0]} {cmd[1:3]}; see {logdir}/{len(calls):02d}.log\n'+result.stderr.decode(errors='replace')[-3000:])
        return result.stdout

    def save(path, data):
        path.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')

    report = {'synthetic': True, 'editorialQC': 'NOT PERFORMED; test pattern, tone and invented test labels, not speech',
              'deliveryReady': False, 'fontPath': str(font), 'commands': calls, 'status': 'running'}
    try:
        import numpy as np
        from PIL import Image
        width, height, fps, frames = 360, 640, 30, 72
        duration = frames/fps
        source = out/'synthetic-source.mp4'
        run(['ffmpeg', '-v', 'error', '-n', '-f', 'lavfi', '-i', f'testsrc2=size={width}x{height}:rate={fps}',
             '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000', '-t', duration,
             '-c:v', 'libx264', '-threads', 2, '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ac', 2, source])
        words = [{'text': text, 'start': start, 'end': end} for text, start, end in
                 [('SYNTHETIC', .1, .5), ('render', .6, 1.0), ('test', 1.1, 1.5), ('ONLY', 1.6, 2.2)]]
        save(out/'words.json', words)
        creator = {'version': 1, 'source': str(source), 'outputDir': str(out/'creator'),
                   'sourceWidth': width, 'sourceHeight': height, 'width': width, 'height': height,
                   'fps': fps, 'start': 0, 'end': duration, 'fontPath': str(font), 'words': words,
                   'shots': [{'startFrame': 0, 'endFrame': frames, 'crop': [0, 0, width, height],
                              'reviewed': True, 'syntheticFixtureOnly': True}],
                   'graphics': {'headline': {'text': 'SYNTHETIC TEST ONLY', 'start': 0, 'end': duration},
                                'caption': {'maxWords': 1, 'position': .8}, 'emphasis': {'keywords': ['ONLY']}},
                   'postCaption': 'Synthetic technical smoke fixture. Not editorial content.'}
        save(out/'creator-plan.json', creator)
        run([sys.executable, ROOT/'scripts/fingerprint_creator.py', '--plan', out/'creator-plan.json'])
        # A fixture authorization is NOT editorial approval of any real source.
        podcast = {'version': 1, 'source': {'path': str(source)},
                   'transcript': {'path': str(out/'words.json'), 'units': 'seconds'},
                   'fontPath': str(font), 'outputDir': str(out/'podcast'),
                   'width': width, 'height': height, 'fps': fps,
                   'renderOptions': {'renderOptions': {'muted': True, 'crf': 18}},
                   'clips': [{'id': 'synthetic', 'ranges': [[0, duration]],
                              'headline': 'SYNTHETIC TEST ONLY', 'sourceNotes': 'Generated test pattern and sine tone, no real speech.',
                              'payoff': 'Technical fixture only', 'postCaption': 'Synthetic smoke. Not for publication.',
                              'approval': {'approved': True, 'reviewer': 'synthetic fixture authorization ONLY', 'reviewedAt': 'synthetic-test'},
                              'captions': {'style': 'bold', 'headlineDuration': 1.2},
                              'shots': [{'rangeIndex': 0, 'start': 0, 'end': duration, 'mode': 'contain'}]}]}
        save(out/'podcast-config.json', podcast)
        podcast_cmd = [sys.executable, ROOT/'scripts/podcast_pipeline.py', 'run', '--config', out/'podcast-config.json']
        run(podcast_cmd)
        # Exercise checksum/decode-backed resume too; its own receipt checks own correctness.
        run(podcast_cmd+['--resume'])
        atlas = json.loads((out/'creator/graphics/atlas-manifest.json').read_text())
        band = json.loads((out/'creator/graphics/manifest.json').read_text())
        assert band['frameCount'] == frames and len(atlas['words']) == len(words)
        with Image.open(band['heroPath']) as im:
            assert im.mode == 'RGBA' and im.getchannel('A').getbbox(), 'Missing actual Chrome hero glyphs'
        with Image.open(out/'creator/graphics/bands/frame-000000.png') as im:
            assert not im.getchannel('A').getbbox(), 'Expected blank caption before first word'
        with Image.open(out/'creator/graphics/bands/frame-000009.png') as im:
            assert im.getchannel('A').getbbox(), 'Expected a visible single-word caption'
        outputs = {}
        for label, file in [('creator', out/'creator/final.mp4'), ('podcast', out/'podcast/synthetic/final.mp4')]:
            info = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', file]))
            v = next(s for s in info['streams'] if s['codec_type'] == 'video')
            a = next(s for s in info['streams'] if s['codec_type'] == 'audio')
            assert (v['width'], v['height'], int(v['nb_frames'])) == (width, height, frames)
            assert float(Fraction(v['avg_frame_rate'])) == fps
            assert v['codec_name'] == 'h264' and a['codec_name'] == 'aac'
            assert abs(float(v['duration'])-duration) < .02 and abs(float(a['duration'])-duration) < .06
            run(['ffmpeg', '-v', 'error', '-xerror', '-i', file, '-f', 'null', '-'])
            outputs[label] = {'path': str(file), 'frames': frames, 'width': width, 'height': height,
                              'duration': float(v['duration']), 'fullDecode': 'passed'}
        # Actual encoded creator frames must retain the hero even after the last word ends.
        def rgb(file):
            raw = run(['ffmpeg', '-v', 'error', '-i', file, '-an', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
            return np.frombuffer(raw, dtype=np.uint8).reshape(-1, height, width, 3)
        before, after = rgb(source), rgb(out/'creator/final.mp4')
        with Image.open(band['heroPath']) as im:
            alpha = np.asarray(im.getchannel('A')) > 200
        assert alpha.any()
        hero_deltas = [float(np.abs(after[i][alpha].astype(float)-before[i][alpha]).mean()) for i in [0, 36, 71]]
        assert min(hero_deltas) > 15, f'Persistent encoded hero not detected: {hero_deltas}'
        caption_deltas = []
        for index in [9, 24, 39, 57]:
            with Image.open(out/f'creator/graphics/bands/frame-{index:06d}.png') as im:
                mask = np.asarray(im.getchannel('A')) > 200
            assert mask.any(), f'Empty expected single-word frame {index}'
            top = band['bandTop']
            delta = float(np.abs(after[index, top:top+band['bandHeight']][mask].astype(float)
                                - before[index, top:top+band['bandHeight']][mask]).mean())
            assert delta > 15, f'Encoded caption not detected at frame {index}: {delta}'
            caption_deltas.append(delta)
        run([sys.executable, ROOT/'scripts/check_remotion_frames.py', source,
             out/'creator/final.mp4', '--report', out/'creator/all-frame-check.json'])
        run([sys.executable, ROOT/'scripts/check_remotion_frames.py', out/'podcast/synthetic/picture.mp4',
             out/'podcast/synthetic/final.mp4', '--report', out/'podcast/all-frame-check.json'])
        report.update(status='passed', outputs=outputs, creatorHeroPixelDeltas=hero_deltas,
                      creatorCaptionMaxWords=1, creatorCaptionPixelDeltas=caption_deltas,
                      creatorAllFrameCheck='passed', creatorBrowserCaptures=atlas['browserCaptures'],
                      podcastResume='passed', podcastAllFrameCheck='passed')
    except Exception as exc:
        report.update(status='failed', error=str(exc))
        raise
    finally:
        save(out/'smoke-report.json', report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
