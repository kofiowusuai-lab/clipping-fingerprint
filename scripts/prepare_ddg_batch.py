"""Acquire bounded source contexts and save actual review evidence for the batch."""
import json, math, subprocess, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import cv2
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];O=R/'outputs/creator-engine/Vpd-xFMfCq0/five-clip-batch';p=O/'manifest.json'
rows=json.loads(p.read_text());lock=threading.Lock()
# Review from completed archive first; high-resolution contexts download independently.
for r in rows:
    w=O/r['id'];w.mkdir(exist_ok=True); cap=cv2.VideoCapture(str(R/'.local/uploads/youtube-cache/Vpd-xFMfCq0/scan.mp4'))
    times=[r['start']+.3+(r['end']-r['start']-.6)*k/11 for k in range(12)]
    sheet=Image.new('RGB',(4*428,3*266),'#181818');d=ImageDraw.Draw(sheet)
    for i,t in enumerate(times):
        cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,f=cap.read();assert ok
        im=Image.fromarray(cv2.cvtColor(cv2.resize(f,(428,240)),cv2.COLOR_BGR2RGB));x=i%4*428;y=i//4*266;sheet.paste(im,(x,y+24));d.text((x+5,y+5),f'{t:.3f}s',fill='white')
    cap.release();sheet.save(w/'archive-review.jpg')

def acquire(r):
    w=O/r['id'];a=math.floor(r['start'])-3;b=math.ceil(r['end'])+3;source=w/'source.mp4';log=w/'download.log'
    if not source.exists():
        with log.open('w') as f:
            run=subprocess.run([str(R/'backend/.venv/bin/yt-dlp'),'--no-playlist','-f','136+251/135+251/18','--download-sections',f'*{a}-{b}','--merge-output-format','mp4','--no-progress','-o',str(w/'source.%(ext)s'),'https://www.youtube.com/watch?v=Vpd-xFMfCq0'],stdout=f,stderr=subprocess.STDOUT)
        if run.returncode: raise RuntimeError(f'{r["id"]}: download failed; see {log}')
    data=json.loads(subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(source)],capture_output=True,text=True,check=True).stdout)
    video=next(x for x in data['streams'] if x['codec_type']=='video'); assert float(data['format']['duration'])>=b-a-.3
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-vn','-ar','16000','-ac','1',str(w/'speech.wav')],check=True)
    with lock:
        r.update(source=str(source),archiveOffset=a,sourceWidth=video['width'],sourceHeight=video['height'],sourceDuration=float(data['format']['duration']),status='source-ready');p.write_text(json.dumps(rows,indent=2))
    print(r['id'],'source-ready',flush=True)
with ThreadPoolExecutor(max_workers=2) as executor:list(executor.map(acquire,rows))
assert len(rows)==5 and all(x['status']=='source-ready' for x in rows)
print('All five source contexts acquired and probed',flush=True)
