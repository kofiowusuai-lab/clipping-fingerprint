"""Read-only source audit and local selected-audio verification for Dana prototype."""
import json, subprocess
from pathlib import Path
import cv2
from PIL import Image, ImageDraw
import whisper
R=Path(__file__).resolve().parents[1];O=R/'outputs/premium-dana';O.mkdir(exist_ok=True)
S=R/'.local/uploads/youtube-cache/Q-DFC0AnbY4/full.mp4'
def run(args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout
probe=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(S)]));(O/'source-probe.json').write_text(json.dumps(probe,indent=2))
times=[237.2,240,242,245,250,255,260,266,706.4,710,674,677,681,685,1224,1228,1233,1238,1243,1248,1253,1258]
cap=cv2.VideoCapture(str(S));sheet=Image.new('RGB',(1600,6*250),'#171717');d=ImageDraw.Draw(sheet)
for i,t in enumerate(times):
 cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,f=cap.read()
 if not ok:raise RuntimeError(t)
 img=Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB));img.thumbnail((400,225));x=i%4*400;y=i//4*250;sheet.paste(img,(x,y+25));d.text((x+8,y+6),f'{t:.3f}s',fill='white')
cap.release();sheet.save(O/'source-review.jpg')
model=whisper.load_model(str(R/'.local/cache/whisper/tiny.en.pt'),device='cpu')
for slug,a,b in [('team',1223.7,1259),('quit-drinking',237.0,267.1)]:
 wav=O/f'{slug}-source.wav'
 run(['ffmpeg','-v','error','-y','-ss',str(a),'-i',str(S),'-t',str(b-a),'-vn','-ar','16000','-ac','1',str(wav)])
 result=model.transcribe(str(wav),language='en',word_timestamps=True,fp16=False,temperature=0)
 result['source_start']=a;result['verification_model']='cached local tiny.en, independent verification not forced alignment'
 (O/f'{slug}-whisper.json').write_text(json.dumps(result,indent=2));print(slug,result['text'],flush=True)
print('Source audit complete',flush=True)
