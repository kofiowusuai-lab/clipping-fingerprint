"""Local audio verification for candidate Dana White shorts."""
import json
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env.local',override=True)
sys.path.insert(0,str(ROOT/'backend'))
from src.media.transcription import transcribe_with_whisper
OUT=ROOT/'outputs/dana-review';OUT.mkdir(exist_ok=True)
SOURCE=ROOT/'.local/uploads/youtube-cache/Q-DFC0AnbY4/full.mp4'
for slug,a,b in [('time-freedom',665,724),('leadership',1464,1518),('risk',4266,4302)]:
    wav=OUT/(slug+'.wav')
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(a),'-i',str(SOURCE),'-t',str(b-a),'-vn','-ar','16000','-ac','1',str(wav)],check=True)
    d=transcribe_with_whisper(wav,model_name='tiny.en',language='en')
    d['source_start']=a
    (OUT/(slug+'.json')).write_text(json.dumps(d,indent=2))
    print(json.dumps({'candidate':slug,'text':d.get('text')}),flush=True)
