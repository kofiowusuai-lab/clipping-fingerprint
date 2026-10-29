"""Unit tests plus an opt-in real Chrome/Pillow smoke test, no video encode."""
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from PIL import Image
from creator_caption_band import active_word, generate, pop

ROOT = Path(__file__).resolve().parents[1]


class CaptionBandTests(unittest.TestCase):
    def test_timing(self):
        words = [{'start': .1, 'end': .2}, {'start': .2, 'end': .3}, {'start': .4, 'end': .5}]
        starts = [w['start'] for w in words]
        for t, expected in [(0, None), (.1, 0), (.2, 1), (.3, None), (.4, 2), (.5, None)]:
            self.assertEqual(active_word(words, starts, t), expected)

    def test_pop_formula(self):
        self.assertEqual(pop(0, 1920), (.82, 1920 * .008 * .55))
        scale, y = pop(.08, 1920)
        self.assertAlmostEqual(scale, .82 + .18 * .5 + .12 * .55)
        self.assertAlmostEqual(y, 1920 * .008 * .5 * .55)
        self.assertAlmostEqual(pop(.16, 1920)[0], 1)
        self.assertAlmostEqual(pop(1, 1920)[1], 0)

    @unittest.skipUnless(os.environ.get('CREATOR_ATLAS_SMOKE') == '1', 'Set CREATOR_ATLAS_SMOKE=1 for real Chrome test')
    def test_real_chrome_smoke(self):
        with tempfile.TemporaryDirectory(prefix='creator-band-smoke-') as tmp:
            base = Path(tmp)
            output = base / 'render'
            job = {'outputDir': str(output), 'fontPath': str(ROOT / 'backend/fonts/Poppins-ExtraBold.ttf'),
                   'width': 240, 'height': 426, 'fps': 30, 'durationInFrames': 20,
                   'headline': 'REAL HERO', 'keywords': ['FAST'], 'captionY': .8,
                   'words': [{'text': 'FAST', 'start': 0, 'end': .3}, {'text': 'creator', 'start': .3, 'end': .6}]}
            job_file = base / 'job.json'
            job_file.write_text(json.dumps(job))
            subprocess.run(['node', str(ROOT / 'remotion/render-creator-atlas.mjs'), str(job_file)], check=True, capture_output=True, text=True)
            manifest = generate(output / 'atlas-manifest.json')
            files = sorted((output / 'bands').glob('frame-*.png'))
            self.assertEqual(len(files), 20)
            self.assertEqual(manifest['browserCaptures'], 2)
            self.assertEqual(manifest['bandHeight'], math.ceil(200 * 240 / 1080))
            self.assertLess(manifest['uniqueFramesWritten'], 20)
            for f in files:
                with Image.open(f) as im:
                    self.assertEqual(im.mode, 'RGBA')
                    self.assertEqual(im.size, (240, manifest['bandHeight']))
                    self.assertEqual(im.getchannel('A').getextrema()[0], 0)
            with Image.open(files[0]) as first, Image.open(files[5]) as settled:
                self.assertIsNotNone(first.getchannel('A').getbbox())
                self.assertNotEqual(first.tobytes(), settled.tobytes())
                pixels = settled.tobytes()
                self.assertTrue(any(pixels[i + 1] > 230 and 170 < pixels[i] < 240
                                    and pixels[i + 2] < 100 and pixels[i + 3] > 240
                                    for i in range(0, len(pixels), 4)))
            with Image.open(files[14]) as normal:
                self.assertTrue(any(normal.getpixel((x, y)) == (255, 255, 255, 255)
                                    for y in range(normal.height) for x in range(normal.width)))
            with Image.open(files[-1]) as blank:
                self.assertIsNone(blank.getchannel('A').getbbox())
            with Image.open(manifest['heroPath']) as hero:
                self.assertEqual(hero.mode, 'RGBA')
                self.assertEqual(hero.size, (240, 426))
                self.assertIsNotNone(hero.getchannel('A').getbbox())
                self.assertEqual(hero.getchannel('A').getextrema()[0], 0)
            with self.assertRaises(FileExistsError):
                generate(output / 'atlas-manifest.json')
            rejected = subprocess.run(['node', str(ROOT / 'remotion/render-creator-atlas.mjs'), str(job_file)], capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            print(json.dumps({'smoke': 'real Chrome + Pillow passed', **manifest}))


if __name__ == '__main__':
    unittest.main()
