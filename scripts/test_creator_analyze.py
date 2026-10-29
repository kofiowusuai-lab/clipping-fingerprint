"""Technical fixtures only: not source highlights or editorial evidence.

Run: backend/.venv/bin/python -m unittest discover -s scripts -p test_creator_analyze.py -v
"""
import json
import math
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from creator_analyze import (clean_caption, contact_sheets, frames, main, normalize_json3,
                             proposal_windows, transcript_text)


class CaptionTests(unittest.TestCase):
    def test_offsets_cleanup_provenance_and_duration(self):
        raw = {"events": [
            {"tStartMs": 1000, "dDurationMs": 5000, "segs": [
                {"utf8": ">> <c.color>Hey &amp; hello</c>", "tOffsetMs": 200},
                {"utf8": "[laughter]", "tOffsetMs": 1000},
                {"utf8": "there", "tOffsetMs": 1500}]},
            {"tStartMs": 2700, "dDurationMs": 4000, "segs": [{"utf8": "friend"}]},
            {"tStartMs": 9000, "segs": [{"utf8": "outside"}]},
            {"aAppend": 1, "tStartMs": 800, "segs": [{"utf8": "\n"}]}]}
        result = normalize_json3(raw, 3.1)
        words = result["words"]
        self.assertEqual([w["text"] for w in words], ["Hey", "&", "hello", "there", "friend"])
        self.assertAlmostEqual(words[0]["start"], 1.2)
        self.assertEqual(words[-1]["end"], 3.1)
        self.assertEqual(result["provenance"]["original_json3"], raw)
        self.assertIn(">>", words[0]["provenance"]["raw_segment"])
        self.assertIn("Hey & hello", transcript_text(words))
        self.assert_bounds(words, 3.1)

    def assert_bounds(self, words, duration):
        for word in words:
            self.assertLess(word["start"], word["end"])
            self.assertGreaterEqual(word["start"], 0)
            self.assertLessEqual(word["end"], duration)
        for left, right in zip(words, words[1:]):
            self.assertLessEqual(left["end"], right["start"] + 1e-12)

    def test_overlap_ties_missing_duration_and_empty(self):
        raw = {"events": [
            {"tStartMs": 100, "segs": [{"utf8": "one"}, {"utf8": "two"}]},
            {"tStartMs": 200, "segs": [{"utf8": "three"}]},
            {"tStartMs": 950, "segs": [{"utf8": "last words"}]}]}
        result = normalize_json3(raw, 1)
        self.assertEqual([w["text"] for w in result["words"]], ["one", "two", "three", "last", "words"])
        self.assert_bounds(result["words"], 1)
        self.assertEqual(normalize_json3({}, 5)["words"], [])
        self.assertEqual(clean_caption(">> [applause] (snorts) <b>Hi</b> ♪"), "Hi")


class WindowTests(unittest.TestCase):
    @staticmethod
    def cue(time, kind="audio_energy"):
        return {"time": time, "kinds": [kind], "features": {"rms": .1}}

    def test_order_merging_handles_and_bounds(self):
        cues = [self.cue(99), self.cue(11, "scene_change_sample"), self.cue(10), self.cue(0)]
        windows = proposal_windows(cues, 100)
        self.assertEqual([w["start"] for w in windows], sorted(w["start"] for w in windows))
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0]["start"], 0)
        self.assertEqual(windows[-1]["end"], 100)
        self.assertEqual(len(windows[0]["cues"]), 3)
        for window in windows:
            self.assertEqual(window["status"], "needs_review")
            self.assertTrue(0 <= window["start"] < window["end"] <= 100)
            self.assertTrue(10 <= window["end"] - window["start"] <= 35)

    def test_dense_and_short_sources(self):
        cues = [self.cue(t) for t in range(120)]
        windows = proposal_windows(cues, 120)
        self.assertEqual(sum(len(w["cues"]) for w in windows), 120)
        for window in windows:
            self.assertTrue(10 <= window["end"] - window["start"] <= 35)
        short = proposal_windows([self.cue(1.9)], 2)
        self.assertEqual((short[0]["start"], short[0]["end"]), (0, 2))
        self.assertEqual(proposal_windows([], 50), [])
        self.assertEqual(proposal_windows([self.cue(-1), self.cue(51)], 50), [])
        with self.assertRaises(ValueError):
            proposal_windows([], 100, minimum=40)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class SyntheticTechnicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="creator-technical-fixture-")
        cls.root = Path(cls.temp.name)
        cls.video = cls.root / "synthetic-technical-fixture.mp4"
        # Two-second synthetic motion/tone; not footage or evidence of highlight quality.
        subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i",
                        "testsrc2=size=320x180:rate=10:duration=2", "-f", "lavfi", "-i",
                        "sine=frequency=440:sample_rate=8000:duration=2", "-vf",
                        "drawbox=x=0:y=0:w=iw:h=ih:color=blue:t=fill:enable='gte(t,1)'", "-c:v", "mpeg4",
                        "-q:v", "4", "-c:a", "aac", "-shortest", str(cls.video)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_end_to_end_audio_video_captions_and_contacts(self):
        captions = self.root / "synthetic-captions.json3"
        captions.write_text(json.dumps({"events": [{"tStartMs": 100, "dDurationMs": 1500,
                              "segs": [{"utf8": ">> fixture [tone] words"}]}]}))
        output = self.root / "coarse"
        self.assertEqual(main(["--source", str(self.video), "--output", str(output),
                               "--captions", str(captions)]), 0)
        audio = json.loads((output / "audio-features.json").read_text())
        self.assertEqual(len(audio["samples"]), 4)
        self.assertGreater(audio["samples"][0]["rms"], 0)
        self.assertGreater(audio["samples"][0]["peak"], 0)
        self.assertGreater(audio["samples"][0]["transient"], 0)
        visual = json.loads((output / "visual-features.json").read_text())
        self.assertEqual(len(visual["samples"]), 2)
        self.assertGreater(visual["samples"][1]["motion_absdiff"], 0)
        self.assertGreater(visual["samples"][1]["histogram_distance"], 0)
        self.assertTrue(any("scene_change_sample" in c["kinds"] for c in visual["cues"]))
        self.assertTrue((output / "metadata.json").is_file())
        self.assertIn("fixture words", (output / "transcript.txt").read_text())
        scoretimes = json.loads((output / "scoretimes.json").read_text())
        self.assertEqual([c["time"] for c in scoretimes["cues"]],
                         sorted(c["time"] for c in scoretimes["cues"]))
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertTrue(manifest["complete"])
        self.assertEqual(manifest["status"], "needs_review")
        contacts = json.loads((output / "contacts/index.json").read_text())
        self.assertEqual(len(contacts["samples"]), 1)
        with Image.open(output / "contacts" / contacts["sheets"][0]) as image:
            self.assertEqual(image.size, (1920, 1470))
        with self.assertRaises(SystemExit):
            main(["--source", str(self.video), "--output", str(output)])

    def test_review_finer_sampling_and_face_guard(self):
        output = self.root / "review"
        main(["--source", str(self.video), "--output", str(output), "--start", ".5",
              "--end", "1.5", "--interval", ".25", "--faces"])
        contacts = json.loads((output / "contacts/index.json").read_text())
        self.assertEqual([s["time"] for s in contacts["samples"]], [.5, .75, 1, 1.25])
        self.assertTrue(all("face_detections" in sample for sample in contacts["samples"]))
        self.assertFalse((output / "audio-features.json").exists())
        with self.assertRaises(SystemExit):
            main(["--source", str(self.video), "--output", str(self.root / "bad"), "--faces"])
        with self.assertRaises(SystemExit):
            main(["--source", str(self.video), "--output", str(self.root / "bad"),
                  "--start", "1", "--end", "3"])

    def test_contact_sheet_splitting(self):
        # 2s/.09s = 23 nominal samples, verifies 20-frame sheet cap.
        result = contact_sheets(self.video, self.root / "split", 0, 2, .09)
        self.assertEqual(len(result["samples"]), math.ceil(2 / .09))
        self.assertEqual(len(result["sheets"]), 2)
        self.assertTrue(all(0 <= sample["slot"] < 20 for sample in result["samples"]))

    def test_first_sample_is_start_not_interval_midpoint(self):
        capture = cv2.VideoCapture(str(self.video))
        try:
            ok, first = capture.read()
            self.assertTrue(ok)
        finally:
            capture.release()
        sampled = list(frames(self.video, 0, 2, 20, 320, 180))
        self.assertEqual(len(sampled), 1)
        self.assertEqual(sampled[0][0], 0)
        expected = cv2.cvtColor(first, cv2.COLOR_BGR2RGB)
        self.assertLess(float(np.abs(sampled[0][1].astype(float) - expected).mean()), 2)


if __name__ == "__main__":
    unittest.main()
