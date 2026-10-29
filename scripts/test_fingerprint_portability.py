"""Portable install/progress invariants; no provider, downloads or real media."""
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class FingerprintSafetyTests(unittest.TestCase):
    def test_installer_dry_run_does_not_write_or_copy_credentials(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d)/'new-profile'
            r=subprocess.run([sys.executable,str(ROOT/'scripts/install_fingerprint.py'),'--profile-home',str(home),'--dry-run'],capture_output=True,text=True,check=True)
            data=json.loads(r.stdout);self.assertFalse(data['copiesCredentials']);self.assertFalse(home.exists());self.assertIn('--profile-home',data['mcp']['args'])
    def test_existing_profile_refused_without_modification(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);sentinel=home/'config.yaml';sentinel.write_text('unchanged: true\n')
            r=subprocess.run([sys.executable,str(ROOT/'scripts/install_fingerprint.py'),'--profile-home',str(home)],capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0);self.assertEqual(sentinel.read_text(),'unchanged: true\n');self.assertEqual(len(list(home.iterdir())),1)
    def test_progress_uses_local_state_not_original_bot(self):
        with tempfile.TemporaryDirectory() as d:
            cmd=[sys.executable,str(ROOT/'scripts/fingerprint_progress.py'),'--state-dir',d];id=subprocess.check_output(cmd+['start','Test only','--stages','QA,Deliver'],text=True).strip()
            subprocess.run(cmd+['stage',id,'QA','done'],capture_output=True,check=True);subprocess.run(cmd+['finish',id,'--fail','--summary','test end'],capture_output=True,check=True)
            data=json.loads(subprocess.check_output(cmd+['show',id],text=True));self.assertTrue(data['closed']);self.assertEqual(data['result'],'failed');self.assertEqual(data['transport'],'local');self.assertNotIn('chat_id',data)
    def test_creator_style_is_single_word_and_podcast_separate(self):
        c=json.loads((ROOT/'configs/creator/styles.json').read_text());self.assertEqual(c['clean-energy']['caption']['maxWords'],1);self.assertEqual(c['aggressive']['caption']['maxWords'],1)
        p=json.loads((ROOT/'configs/visuals/podcast-bold.json').read_text());self.assertEqual(p['captionStyle']['fontSizeRatio'],.095);self.assertGreater(p['captionStyle']['maxWords'],1)
if __name__=='__main__':unittest.main()
