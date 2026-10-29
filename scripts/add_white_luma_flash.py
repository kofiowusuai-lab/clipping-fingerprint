"""Smooth exposure bloom to white at the approved riser/scene cut."""
import json
import subprocess
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path)
parser.add_argument('--output-dir',type=Path)
parser.add_argument('--output-name',default='03-setbacks-white-luma-flash.mp4')
parser.add_argument('--cut-seconds',type=float,default=3.8)
args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[1]
SRC=args.source or ROOT/'outputs/serhant-v5/03-setbacks-supplied-riser.mp4'
OUT=args.output_dir or ROOT/'outputs/serhant-v6'; OUT.mkdir(exist_ok=True)
FINAL=OUT/args.output_name
FF=imageio_ffmpeg.get_ffmpeg_exe()
cap=cv2.VideoCapture(str(SRC))
fps=30
# Three-frame eased rise; eight-frame eased recovery. One isolated transition.
cut=round(args.cut_seconds*fps); begin=cut-3; end=cut+8
p=subprocess.Popen([FF,'-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','720x1280','-r','30','-i','pipe:0','-i',str(SRC),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','20','-maxrate','1800k','-bufsize','3600k','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(FINAL)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
sheet=Image.new('RGB',(1440,1340),'#171717'); draw=ImageDraw.Draw(sheet)
review_frames=[cut-4,cut-2,cut-1,cut,cut+1,cut+3,cut+6,cut+9]
levels=[]; count=0
while True:
    ok,frame=cap.read()
    if not ok: break
    strength=0.0
    if begin<=count<=end:
        phase=(count-begin)/(cut-begin) if count<=cut else (end-count)/(end-cut)
        strength=(1-np.cos(np.pi*phase))/2
        # Raise exposure/highlights first, then bloom completely to white.
        x=frame.astype(np.float32)/255
        exposed=np.minimum(1,x*(1+1.6*strength))
        white_mix=strength**1.45
        x=exposed*(1-white_mix)+white_mix
        frame=np.rint(x*255).clip(0,255).astype(np.uint8)
        levels.append({'frame':count,'time':count/fps,'strength':float(strength),'mean':float(frame.mean())})
    if count in review_frames:
        i=review_frames.index(count); x=(i%4)*360; y=(i//4)*670
        sheet.paste(Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)).resize((360,640)),(x,y+25)); draw.text((x+8,y+6),f'{count/fps:.3f}s',fill='white')
    p.stdin.write(frame.tobytes()); count+=1
cap.release(); p.stdin.close(); error=p.stderr.read(); assert p.wait()==0,error.decode()
assert any(v['frame']==cut and v['mean']==255 for v in levels)
sheet.save(OUT/'transition-review.jpg')
def run(args):
    r=subprocess.run(args,capture_output=True,text=True,check=True)
    return r
probe=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(FINAL)]).stdout)
v=next(s for s in probe['streams'] if s['codec_type']=='video'); a=next(s for s in probe['streams'] if s['codec_type']=='audio')
assert (v['width'],v['height'])==(720,1280)
assert abs(float(v['duration'])-float(a['duration']))<.05
assert not run([FF,'-v','error','-i',str(FINAL),'-f','null','-']).stderr.strip()
# Verify copied audio packets, not just stream labels, preserve approved mix.
def audio_hash(path):
    return run([FF,'-v','error','-i',str(path),'-map','0:a:0','-c','copy','-f','hash','-hash','sha256','-']).stdout.strip()
assert audio_hash(SRC)==audio_hash(FINAL)
result={'path':str(FINAL),'duration':probe['format']['duration'],'bytes':FINAL.stat().st_size,'frames':count,'flash_peak_and_cut':cut/fps,'flash_start':begin/fps,'flash_end':end/fps,'approved_audio':'packet hash identical','full_decode':'passed','flash_envelope':levels}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
