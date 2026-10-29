#!/usr/bin/env python3
"""Fast creator graphics: Chrome captures static atlases; Pillow animates RGBA bands.

Usage: backend/.venv/bin/python scripts/creator_caption_band.py /absolute/job.json
Or: ... --atlas-manifest /absolute/output/atlas-manifest.json
Times are clip-relative seconds; word end is exclusive. Output is never overwritten.
"""
from __future__ import annotations
import argparse
import bisect
import json
import math
import os
from pathlib import Path
import subprocess
from PIL import Image


def pop(age: float, height: int) -> tuple[float, float]:
    intro = max(0.0, min(1.0, age / .16))
    rise = intro * intro * (3 - 2 * intro)
    return (.82 + .18 * rise + math.sin(math.pi * intro) * .12 * .55,
            height * .008 * (1 - rise) * .55)


def active_word(words: list[dict], starts: list[float], time: float) -> int | None:
    index = bisect.bisect_right(starts, time) - 1
    return index if index >= 0 and time < words[index]['end'] else None


def generate(atlas_file: Path) -> dict:
    atlas_file = atlas_file.resolve(strict=True)
    data = json.loads(atlas_file.read_text())
    width, height, fps = data['width'], data['height'], data['fps']
    count = data['durationInFrames']
    if not all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in (width, height, fps, count)):
        raise ValueError('Invalid atlas dimensions/timing')
    words = data['words']
    previous = 0.0
    for word in words:
        if not (isinstance(word['text'], str) and math.isfinite(word['start']) and math.isfinite(word['end'])
                and previous <= word['start'] < word['end'] <= count / fps
                and isinstance(word['sprite'], int) and 0 <= word['sprite'] < len(data['sprites'])):
            raise ValueError('Invalid or overlapping atlas words')
        previous = word['end']
    band_height = math.ceil(200 * width / 1080)
    center = data['captionY'] * height
    band_top = round(center - band_height / 2)
    if not 0 <= band_top <= height - band_height:
        raise ValueError('Caption band exceeds canvas')
    root = atlas_file.parent
    def local_file(value: str) -> Path:
        p = Path(value).resolve(strict=True)
        if not p.is_relative_to(root):
            raise ValueError('Atlas asset must be inside output directory')
        return p
    hero = local_file(data['heroPath'])
    with Image.open(hero) as im:
        if im.mode != 'RGBA' or im.size != (width, height):
            raise ValueError('Hero must be full-canvas RGBA')
    sprites = []
    for sprite in data['sprites']:
        with Image.open(local_file(sprite['page'])) as page:
            x, y, w, h = (sprite[k] for k in ('x', 'y', 'width', 'height'))
            if x < 0 or y < 0 or x + w > page.width or y + h > page.height:
                raise ValueError('Sprite outside atlas')
            cell = page.convert('RGBA').crop((x, y, x + w, y + h))
        bbox = cell.getchannel('A').getbbox()
        if bbox is None:
            raise ValueError('Empty glyph sprite')
        if bbox[0] == 0 or bbox[1] == 0 or bbox[2] == w or bbox[3] == h:
            raise ValueError('Glyph touches cell edge; increase cell padding')
        sprites.append((cell.crop(bbox), bbox[0] - w / 2, bbox[1] - h / 2))
    # Exclusive output claim. Never clear an old render or replace frames/manifests.
    if (root / 'manifest.json').exists():
        raise FileExistsError('manifest.json already exists')
    output = root / 'bands'
    output.mkdir()
    starts = [w['start'] for w in words]
    cache: dict[tuple, Path] = {}
    unique = 0
    for frame in range(count):
        time = frame / fps
        index = active_word(words, starts, time)
        scale, dy = pop(time - words[index]['start'], height) if index is not None else (1, 0)
        key = (words[index]['sprite'], round(scale, 12), round(dy, 12)) if index is not None else ('blank',)
        target = output / f'frame-{frame:06d}.png'
        if key in cache:
            try:
                os.link(cache[key], target)
            except OSError:
                import shutil
                shutil.copyfile(cache[key], target)
            continue
        band = Image.new('RGBA', (width, band_height))
        if index is not None:
            glyph, left, top = sprites[words[index]['sprite']]
            resized = glyph.resize((max(1, round(glyph.width * scale)), max(1, round(glyph.height * scale))), Image.Resampling.LANCZOS)
            x = round(width / 2 + left * scale)
            y = round(center - band_top + top * scale + dy)
            if x < 0 or y < 0 or x + resized.width > width or y + resized.height > band_height:
                raise ValueError(f'Animated glyph exceeds band at frame {frame}')
            band.alpha_composite(resized, (x, y))
        band.save(target, compress_level=1)
        cache[key] = target
        unique += 1
    files = sorted(output.glob('frame-*.png'))
    if len(files) != count:
        raise RuntimeError('Incomplete caption sequence')
    manifest = {'version': 1, 'kind': 'creator-caption-band', 'width': width, 'height': height,
                'fps': fps, 'durationInFrames': count, 'frameCount': count, 'startNumber': 0,
                'bandTop': band_top, 'bandHeight': band_height, 'bandWidth': width,
                'heroPath': str(hero), 'alpha': True, 'ffmpegPattern': str(output / 'frame-%06d.png'),
                'pngPattern': str(output / 'frame-%06d.png'), 'uniqueFramesWritten': unique,
                'browserCaptures': data.get('browserCaptures'), 'atlasManifest': str(atlas_file)}
    with (root / 'manifest.json').open('x') as f:
        json.dump(manifest, f, indent=2)
        f.write('\n')
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', nargs='?', type=Path)
    parser.add_argument('--atlas-manifest', type=Path)
    args = parser.parse_args()
    if bool(args.job) == bool(args.atlas_manifest):
        parser.error('Supply exactly one job JSON or --atlas-manifest')
    if args.job:
        if not args.job.is_absolute():
            parser.error('job must be absolute')
        job = json.loads(args.job.read_text())
        script = Path(__file__).resolve().parents[1] / 'remotion/render-creator-atlas.mjs'
        subprocess.run(['node', str(script), str(args.job)], check=True, stdout=subprocess.DEVNULL)
        atlas = Path(job['outputDir']) / 'atlas-manifest.json'
    else:
        atlas = args.atlas_manifest
    print(json.dumps(generate(atlas)))


if __name__ == '__main__':
    main()
