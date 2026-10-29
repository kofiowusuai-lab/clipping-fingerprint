"""Unit tests plus optional real FFmpeg/Remotion integration (no Dana renders)."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import podcast_pipeline as pipeline


def example():
    return {
        'version': 1, 'source': {'path': 'source.mp4', 'url': 'https://example.org/source'},
        'transcript': {'path': 'words.json', 'units': 'milliseconds'},
        'outputDir': 'output', 'fontPath': 'font.ttf', 'width': 1080, 'height': 1920, 'fps': 30,
        'clips': [{'id': 'one', 'ranges': [[10, 12], [2, 4]], 'shots': [],
                   'headline': 'A truthful hook', 'sourceNotes': 'Manual review',
                   'payoff': 'Complete answer', 'postCaption': 'Copy #podcast',
                   'approval': {'approved': False}, 'captions': {'style': 'bold'}, 'graphics': {}}],
    }


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.raw = example()
        self.base = Path('/tmp/podcast-config-test').resolve()

    def validate(self):
        return pipeline.validate_config(self.raw, self.base)

    def test_resolves_paths_relative_to_config_not_cwd(self):
        c = self.validate()
        self.assertEqual(c['source']['path'], str(self.base/'source.mp4'))
        self.assertEqual(c['outputDir'], str(self.base/'output'))
        self.assertEqual(self.raw['source']['path'], 'source.mp4')

    def test_defaults_and_url_only(self):
        del self.raw['source']['path']
        for key in ('width', 'height', 'fps'):
            del self.raw[key]
        c = self.validate()
        self.assertEqual((c['width'], c['height'], c['fps']), (1080, 1920, 30))

    def test_contract_version_and_explicit_units(self):
        for field, value in [('version', 2), ('version', None)]:
            with self.subTest(value=value):
                self.raw[field] = value
                with self.assertRaises(ValueError):
                    self.validate()
        self.raw = example()
        del self.raw['transcript']['units']
        with self.assertRaises(ValueError):
            self.validate()

    def test_unsafe_duplicate_ids(self):
        for slug in ('../oops', '/absolute', '', 'space name'):
            self.raw['clips'][0]['id'] = slug
            with self.assertRaises(ValueError):
                self.validate()
        self.raw = example()
        self.raw['clips'].append(copy.deepcopy(self.raw['clips'][0]))
        with self.assertRaises(ValueError):
            self.validate()

    def test_output_does_not_enclose_inputs(self):
        self.raw['outputDir'] = '.'
        with self.assertRaises(ValueError):
            self.validate()
        self.raw['outputDir'] = 'source.mp4'
        with self.assertRaises(ValueError):
            self.validate()

    def test_finite_nonempty_ranges(self):
        for pair in ([1, 1], [-1, 2], [1, float('nan')], [2, 1], [1, 1.001], [True, 2]):
            self.raw['clips'][0]['ranges'] = [pair]
            with self.assertRaises(ValueError):
                self.validate()

    def test_no_pipeline_overrides_but_arbitrary_js_props(self):
        self.raw['clips'][0]['renderOptions'] = {'futureSupportedProp': {'x': 1}}
        self.validate()
        for key in pipeline.RESERVED:
            self.raw['clips'][0]['renderOptions'] = {key: 'bad'}
            with self.assertRaises(ValueError):
                self.validate()

    def test_approval_needs_provenance(self):
        clip = self.raw['clips'][0]
        with self.assertRaises(ValueError):
            pipeline.require_approval(clip)
        clip['approval']['approved'] = True
        with self.assertRaises(ValueError):
            self.validate()
        clip['approval'].update(reviewer='Editor', reviewedAt='2026-10-28')
        self.validate()
        pipeline.require_approval(clip)

    def test_shots_must_partition_all_ranges(self):
        self.raw['clips'][0]['shots'] = [{'rangeIndex': 0, 'start': 10, 'end': 12, 'mode': 'contain'}]
        with self.assertRaises(ValueError):
            self.validate()
        self.raw['clips'][0]['shots'].append({'rangeIndex': 1, 'start': 2, 'end': 4, 'mode': 'contain'})
        self.validate()
        self.raw['clips'][0]['shots'][1]['start'] = 2.1
        with self.assertRaises(ValueError):
            self.validate()

    def test_manual_crop_requires_review_and_monotonic_track(self):
        self.raw['clips'][0]['ranges'] = [[10, 12]]
        shot = {'rangeIndex': 0, 'start': 10, 'end': 12, 'mode': 'crop', 'crop': {'x': 0, 'y': 0, 'width': 100, 'height': 200}}
        self.raw['clips'][0]['shots'] = [shot]
        with self.assertRaises(ValueError):
            self.validate()
        shot['reviewed'] = True
        self.validate()
        shot['track'] = [{'time': 1, 'x': 0, 'y': 0}, {'time': .5, 'x': 2, 'y': 0}]
        with self.assertRaises(ValueError):
            self.validate()

    def test_reaction_hold(self):
        self.raw['clips'][0]['ranges'] = [[10, 12]]
        self.raw['clips'][0]['shots'] = [{'rangeIndex': 0, 'start': 10, 'end': 12, 'mode': 'contain', 'reaction': True}]
        with self.assertRaises(ValueError):
            self.validate()

    def test_riser_only_semantic_cut_with_backtime(self):
        riser = {'path': 'riser.wav', 'crestSeconds': 1.78, 'cutSeconds': 2, 'semanticNote': 'Completed hook'}
        self.raw['clips'][0]['riser'] = riser
        self.validate()
        riser['cutSeconds'] = 3
        with self.assertRaises(ValueError):
            self.validate()
        riser['cutSeconds'] = 2
        riser['crestSeconds'] = 3
        with self.assertRaises(ValueError):
            self.validate()


class TimelineTests(unittest.TestCase):
    def test_millisecond_remap_reorders_and_trims_at_cut(self):
        words = [{'text': 'Earlier', 'start': 2100, 'end': 2300}, {'text': '>> Hook', 'start': 10100, 'end': 10400}, {'text': 'end', 'start': 11900, 'end': 12200}]
        actual = pipeline.remap_words(words, [[10, 12], [2, 4]], 30, 'milliseconds')
        self.assertEqual(actual, [{'text': 'Hook', 'start': .1, 'end': .4}, {'text': 'end', 'start': 1.9, 'end': 2.0}, {'text': 'Earlier', 'start': 2.1, 'end': 2.3}])

    def test_frame_rounding_changes_next_offset(self):
        actual = pipeline.remap_words([{'text': 'a', 'start': 5.1, 'end': 5.2}], [[0, 1.01], [5, 6]], 30, 'seconds')
        self.assertEqual(actual[0]['start'], 1.1)

    def test_skip_display_cues_and_words_whose_onsets_precede_range(self):
        words = [{'text': '[snorts]', 'start': 0, 'end': .1}, {'text': 'cut', 'start': .5, 'end': 1.2}, {'text': 'complete', 'start': 1.3, 'end': 1.5}]
        self.assertEqual(pipeline.remap_words(words, [[1, 2]], 30, 'seconds'), [{'text': 'complete', 'start': .3, 'end': .5}])

    def test_bad_words_rejected(self):
        for words in ([{'text': 'x', 'start': 1, 'end': .5}], [{'text': 'x', 'start': 0, 'end': 1}, {'text': 'y', 'start': .5, 'end': 2}]):
            with self.assertRaises(ValueError):
                pipeline.remap_words(words, [[0, 3]], 30, 'seconds')

    def test_contact_sheet_cuts_and_last_frame(self):
        times = pipeline.qa_times(4, [2], 30)
        self.assertIn(2, times)
        self.assertIn(round(2-1/30, 6), times)
        self.assertIn(round(4-1/30, 6), times)
        self.assertEqual(times, sorted(set(times)))

    def test_manual_crop_bounds(self):
        shot = {'crop': {'x': 900, 'y': 0, 'width': 200, 'height': 300}}
        with self.assertRaises(ValueError):
            pipeline.crop_filter(shot, 1000, 600, 1080, 1920)

    def test_crop_interpolation_is_piecewise_smooth(self):
        expression = pipeline.interpolation([{'time': 0, 'x': 20}, {'time': 1, 'x': 40}, {'time': 2, 'x': 30}], 'x')
        self.assertIn('if(lt(t,1.000000)', expression)
        self.assertIn('clip(', expression)


class ReceiptTests(unittest.TestCase):
    def test_requires_matching_key_and_all_checksums(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            path = work/'artifact.json'
            path.write_text('{}')
            pipeline.save_receipt(work, 'prepare', 'key', [path])
            self.assertTrue(pipeline.receipt_valid(work, 'prepare', 'key'))
            self.assertFalse(pipeline.receipt_valid(work, 'prepare', 'changed'))
            path.write_text('{"changed":true}')
            self.assertFalse(pipeline.receipt_valid(work, 'prepare', 'key'))

    def test_partial_media_never_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            path = work/'picture.mp4'
            path.write_bytes(b'partial')
            pipeline.save_receipt(work, 'prepare', 'key', [path])
            with patch.object(pipeline, 'decode', side_effect=RuntimeError('bad decode')):
                self.assertFalse(pipeline.receipt_valid(work, 'prepare', 'key'))

    def test_only_unknown_ids_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg = Path(directory)/'config.json'
            cfg.write_text(json.dumps(example()))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(pipeline.main(['inspect', '--config', str(cfg), '--only', 'unknown']), 1)


class WorkflowMoreTests(unittest.TestCase):
    def test_video_end_requires_review_and_retained_frame(self):
        c = example()
        c['clips'][0]['ranges'] = [[10, 12]]
        shot = {'rangeIndex': 0, 'start': 10, 'end': 12, 'mode': 'contain', 'videoEnd': 11.8}
        c['clips'][0]['shots'] = [shot]
        with self.assertRaises(ValueError):
            pipeline.validate_config(c, Path('/tmp'))
        shot['reviewed'] = True
        pipeline.validate_config(c, Path('/tmp'))
        shot['videoEnd'] = 12.1
        with self.assertRaises(ValueError):
            pipeline.validate_config(c, Path('/tmp'))

    def test_fingerprint_changes_for_config_and_input_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for name in ('source.mp4', 'words.json', 'font.ttf'):
                (base/name).write_bytes(b'fixture')
            c = pipeline.validate_config(example(), base)
            with patch.object(pipeline, 'ROOT', base):
                key = pipeline.fingerprint(c)
                self.assertEqual(key, pipeline.fingerprint(c))
                c['clips'][0]['headline'] += ' changed'
                self.assertNotEqual(key, pipeline.fingerprint(c))
                key = pipeline.fingerprint(c)
                (base/'source.mp4').write_bytes(b'changed source')
                self.assertNotEqual(key, pipeline.fingerprint(c))

    def test_local_checkpoint_source_offset_units_and_no_overwrite(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base/'tiny.en.pt').write_bytes(b'trusted-test-double')
            (base/'source.mp4').write_bytes(b'fixture')
            c = pipeline.validate_config(example(), base)
            fake_model = SimpleNamespace(transcribe=lambda *a, **k: {'segments': [{'words': [{'word': ' hello ', 'start': .1, 'end': .4}]}]})
            loader = Mock(return_value=fake_model)
            fake_whisper = SimpleNamespace(load_model=loader)
            with patch.dict('sys.modules', {'whisper': fake_whisper}), patch.object(pipeline, 'command'):
                pipeline.transcribe(c, base/'tiny.en.pt', 10, 12, False)
                loader.assert_called_once_with(str((base/'tiny.en.pt').resolve()), device='cpu')
                cache = json.loads((base/'words.json').read_text())
                self.assertEqual(cache['words'][0], {'text': 'hello', 'start': 10100, 'end': 10400, 'speaker': None})
                with self.assertRaises(ValueError):
                    pipeline.transcribe(c, base/'tiny.en.pt', 10, 12, False)
                with self.assertRaises(FileNotFoundError):
                    pipeline.transcribe(c, base/'missing.pt', 10, 12, True)


@unittest.skipUnless(os.environ.get('PODCAST_INTEGRATION') == '1', 'Set PODCAST_INTEGRATION=1 for real local FFmpeg/Remotion test')
class IntegrationTests(unittest.TestCase):
    def test_real_local_checkpoint_transcription(self):
        checkpoint = pipeline.ROOT/'.local/cache/whisper/tiny.en.pt'
        if not checkpoint.is_file():
            self.skipTest('Existing local tiny.en checkpoint unavailable; no download attempted')
        with tempfile.TemporaryDirectory(prefix='podcast-whisper-test-') as directory:
            base = Path(directory)
            pipeline.command(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=16000:duration=1', '-c:a', 'aac', base/'source.mp4'])
            cfg = base/'config.json'
            cfg.write_text(json.dumps(example()))
            self.assertEqual(pipeline.main(['transcribe', '--config', str(cfg), '--model-path', str(checkpoint), '--transcribe-start', '.1', '--transcribe-end', '.8']), 0)
            cache = json.loads((base/'words.json').read_text())
            self.assertEqual(cache['engine'], 'local-whisper')
            self.assertEqual(cache['units'], 'milliseconds')
            self.assertEqual(cache['sourceOffsetSeconds'], .1)

    def test_real_new_source_prepare_render_qa_resume(self):
        with tempfile.TemporaryDirectory(prefix='podcast-pipeline-') as directory:
            base = Path(directory)
            source = base/'source.mp4'
            pipeline.command(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=30:duration=3', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=3', '-c:v', 'libx264', '-crf', 19, '-pix_fmt', 'yuv420p', '-c:a', 'aac', source])
            (base/'words.json').write_text(json.dumps({'words': [{'text': 'TEST', 'start': 100, 'end': 700}, {'text': 'ONLY', 'start': 1600, 'end': 2200}]}))
            c = example()
            c.update(width=180, height=320, fontPath=str(pipeline.ROOT/'backend/fonts/Poppins-ExtraBold.ttf'), renderOptions={'renderOptions': {'crf': 18, 'muted': True, 'audioBitrate': '192k'}})
            clip = c['clips'][0]
            clip.update(ranges=[[0, 1], [1.5, 2.5]], headline='TEST', approval={'approved': True, 'reviewer': 'Synthetic integration test', 'reviewedAt': 'test fixture'})
            clip['shots'] = [{'rangeIndex': 0, 'start': 0, 'end': 1, 'mode': 'contain'}, {'rangeIndex': 1, 'start': 1.5, 'end': 2.5, 'videoEnd': 2.3, 'mode': 'crop', 'reviewed': True, 'crop': {'x': 110, 'y': 0, 'width': 100, 'height': 178}, 'track': [{'time': 0, 'x': 110, 'y': 0}, {'time': .8, 'x': 115, 'y': 0}]}]
            cfg = base/'config.json'
            cfg.write_text(json.dumps(c))
            self.assertEqual(pipeline.main(['run', '--config', str(cfg)]), 0)
            work = base/'output/one'
            report = json.loads((work/'qa.json').read_text())
            self.assertEqual(report['visualReview'], 'pending')
            self.assertFalse(report['deliveryReady'])
            self.assertEqual(report['fullDecode'], 'passed')
            self.assertGreater(report['audio']['peak'], 0)
            self.assertTrue((work/'contact-sheet.jpg').is_file())
            info = json.loads((work/'prepare.json').read_text())
            self.assertAlmostEqual(info['shots'][1]['tailHold'], .2)
            normalized = pipeline.load_config(cfg)
            # Concurrent renderer edits correctly invalidate receipts. Hold the
            # initial key constant only for this isolated cache mechanics test.
            initial_key = json.loads((work/'prepare.receipt.json').read_text())['fingerprint']
            previous = (work/'final.mp4').stat().st_mtime_ns
            with patch.object(pipeline, 'fingerprint', return_value=initial_key):
                self.assertEqual(pipeline.main(['run', '--config', str(cfg), '--resume', '--only', 'one']), 0)
            self.assertEqual((work/'final.mp4').stat().st_mtime_ns, previous)
            # Tampered output cannot be accepted by resume.
            (work/'final.mp4').write_bytes(b'incomplete')
            key = pipeline.dependency_key(initial_key, work, 'prepare')
            self.assertFalse(pipeline.receipt_valid(work, 'render', key))


if __name__ == '__main__':
    unittest.main()
