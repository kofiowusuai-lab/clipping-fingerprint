"""Regression tests for read-only input preservation and graphics invalidation."""
import copy,importlib.util,json,os,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('podcast_pipeline',Path(__file__).with_name('podcast_pipeline.py'));p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
R=Path(__file__).resolve().parents[1]
class InputSafetyTests(unittest.TestCase):
 def test_transcript_cannot_replace_source_or_font(self):
  raw=json.loads((R/'configs/podcast/example.json').read_text());base=R/'configs/podcast'
  for target in [raw['source']['path'],raw['fontPath']]:
   c=copy.deepcopy(raw);c['transcript']['path']=target
   with self.assertRaisesRegex(ValueError,'alias'):p.validate_config(c,base)
 def test_hardlink_alias(self):
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'source.mp4';b=Path(d)/'transcript.json';a.write_bytes(b'fixture');os.link(a,b)
   c=json.loads((R/'configs/podcast/example.json').read_text());c['source']['path']=str(a);c['transcript']['path']=str(b)
   with self.assertRaisesRegex(ValueError,'alias'):p.validate_config(c,R/'configs/podcast')
 def test_optional_graphics_change_invalidates_resume(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);inputs=[]
   for name in ['source.mp4','words.json','font.ttf','logo.png']:
    f=d/name;f.write_bytes(b'fixture');inputs.append(str(f))
   c={'source':{'path':inputs[0]},'transcript':{'path':inputs[1]},'fontPath':inputs[2],'clips':[],'renderOptions':{'overlays':[{'imagePath':inputs[3]}]}}
   first=p.fingerprint(c);Path(inputs[3]).write_bytes(b'changed fixture');self.assertNotEqual(first,p.fingerprint(c))
if __name__=='__main__':unittest.main()
