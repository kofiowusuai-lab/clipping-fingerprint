"""Prepare the complete no-insert Dana edit for the corrected Remotion pass."""
import json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs/remotion-corrected';W=R/'outputs/dana-no-inserts/01-time-freedom'
m=json.loads((W.parent/'manifest.json').read_text())[0]
subprocess.run(['ffmpeg','-v','error','-y','-i',str(W/'picture.mp4'),'-i',str(W/'mix.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','128k','-movflags','+faststart',str(O/'prepared-full.mp4')],check=True)
words=json.loads((R/'.local/uploads/youtube-cache/Q-DFC0AnbY4/full.transcript_cache.json').read_text())['words']
for w in words:
 if 677600<=w['start']<=677800 and w['text']=='Bad':w['end']=678040
words.append({'text':'shit','start':678040,'end':678280});words.sort(key=lambda w:w['start'])
mapped=[];offset=0
for a,b in m['audio_ranges']:
 for w in words:
  if a*1000<=w['start']<b*1000:
   text=w['text'].replace('>>','').strip()
   if not text or text.startswith('['):continue
   mapped.append({'text':text,'start':round(offset+w['start']/1000-a,6),'end':round(offset+min(b,w['end']/1000)-a,6)})
 offset+=b-a
(O/'words.json').write_text(json.dumps(mapped,indent=2))
print(json.dumps({'cut':m['riser_crest_and_white_flash'],'riser_start':m['riser_start'],'words':len(mapped),'audio_source':str(W/'mix.wav')}))
