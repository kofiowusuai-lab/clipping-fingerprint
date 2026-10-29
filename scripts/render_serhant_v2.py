"""Hand-edited podcast shorts: purposeful punch-ins, face crops, bold captions."""
import json
import math
import re
import statistics
import subprocess
import sys
from pathlib import Path

import cv2
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from src.media.face_detection import YuNetFaceDetector

SOURCE = ROOT / '.local/uploads/youtube-cache/K213Pn9ffIc/full.mp4'
OUT = ROOT / 'outputs/serhant-v2'
OUT.mkdir(parents=True, exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
WORDS = json.loads(SOURCE.with_suffix('.transcript_cache.json').read_text())['words']
FONT = ImageFont.truetype(str(ROOT / 'backend/fonts/Poppins-ExtraBold.ttf'), 60)
DETECTOR = YuNetFaceDetector()
CAP = cv2.VideoCapture(str(SOURCE))
# Cuts follow the argument and emphasis, not a timer. 3 removes the job-list
# detour and brings the original setback statement forward as the hook.
EDITS = [
 {'slug':'03-setbacks-recut','title':'Setbacks are speed bumps', 'beats':[(403.14,406.56,1.10),(450.12,456.18,1.0),(466.14,472.88,1.0),(472.88,480.02,1.13),(480.02,486.88,1.0),(486.88,488.76,1.16)]},
 {'slug':'02-negotiators-recut','title':'The best negotiators translate', 'beats':[(3156.25,3161.28,1.1),(3161.28,3172.99,1.0),(3172.99,3177.77,1.13),(3177.77,3182.41,1.0),(3182.41,3191.09,1.12)]},
 {'slug':'01-confidence-recut','title':'Confidence is currency', 'beats':[(1542.50,1551.56,1.1),(1551.56,1558.86,1.0),(1558.86,1569.30,1.0),(1570.10,1575.55,1.1),(1576.15,1586.65,1.16)]},
]

def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-6000:])
    return r


def cuts(a,b):
    # Detect original camera changes too, so a crop never stays on an empty seat.
    r = run([FFMPEG,'-hide_banner','-ss',str(a),'-i',str(SOURCE),'-t',str(b-a),'-an','-vf',"select='gt(scene,0.25)',showinfo",'-fps_mode','vfr','-f','null','-'])
    pts = [a+float(s) for s in re.findall(r'pts_time:([\d.]+)',r.stderr)]
    points = [a]
    for t in pts:
        if t-points[-1] > 0.4 and b-t > 0.4:
            points.append(t)
    points.append(b)
    return list(zip(points,points[1:]))


def crop_plan(a,b,punch):
    samples = []
    for i in range(max(2,math.ceil(b-a))):
        t = min(b-0.04,a+0.1+i)
        CAP.set(cv2.CAP_PROP_POS_MSEC,t*1000)
        ok,frame = CAP.read()
        if not ok: continue
        faces = DETECTOR.detect(frame)
        if not faces: continue
        face = max(faces,key=lambda f:f[0]) if len(faces)>1 else faces[0]
        samples.append((t-a,face))
    if not samples: raise RuntimeError(f'No face at {a}')
    fh = statistics.median(f[3] for _,f in samples)
    h = int((930 if fh>250 else 580)/punch)//2*2
    w = int(h*9/16)//2*2
    y = max(0,min(1080-h,int(min(f[1]-.44*f[3] for _,f in samples))))//2*2
    positions = [(t,max(0,min(1920-w,f[0]+f[2]*.5-w*.5))) for t,f in samples]
    smooth=[]
    for i,(t,x) in enumerate(positions):
        smooth.append((t,statistics.mean(p[1] for p in positions[max(0,i-1):i+2])))
    expr=f'{smooth[-1][1]:.2f}'
    for i in range(len(smooth)-2,-1,-1):
        t,x=smooth[i]; nt,nx=smooth[i+1]; dt=max(.01,nt-t)
        expr=f'if(lt(t,{nt:.3f}),({x:.2f}+({nx-x:.2f})*max(0,t-{t:.3f})/{dt:.3f}),{expr})'
    return {'w':w,'h':h,'y':y,'x':expr,'face_samples':samples}


def stamp(t):
    cs=round(max(0,t)*100)
    return f'{cs//360000}:{cs//6000%60:02d}:{cs//100%60:02d}.{cs%100:02d}'


def captions(edit,path):
    mapped=[]; offset=0
    for a,b,_ in edit['beats']:
        for w in WORDS:
            if a*1000<=w['start']<b*1000:
                mapped.append({'text':w['text'].strip().upper(),'start':offset+max(0,w['start']/1000-a),'end':offset+min(b-a,w['end']/1000-a)})
        offset+=b-a
    # Correct a tokenizer-split word in the cached transcript, not the speech.
    if mapped and mapped[0]['text']=='SET' and len(mapped)>1 and mapped[1]['text']=='BACKS':
        mapped[0]['text']='SETBACKS'; mapped[0]['end']=mapped[1]['end']; mapped.pop(1)
    # Keep caption groups inside editorial beats, never across a jump cut.
    boundaries=[]; elapsed=0
    for a,b,_ in edit['beats']:
        elapsed+=b-a; boundaries.append(elapsed)
    groups=[]; group=[]
    for word in mapped:
        test=' '.join(x['text'] for x in group+[word])
        crosses_cut=bool(group) and any(group[-1]['start']<cut<=word['start']+.005 for cut in boundaries)
        if group and (crosses_cut or len(group)>=3 or FONT.getlength(test)>600 or word['start']-group[-1]['end']>.4):
            groups.append(group); group=[]
        group.append(word)
        if word['text'].endswith(('.', '?', '!')):
            groups.append(group); group=[]
    if group: groups.append(group)
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Poppins ExtraBold,60,&H00FFFFFF,&H0000E8FF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,3.5,1.5,2,45,45,270,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events=[]
    for g in groups:
        for i,w in enumerate(g):
            end=g[i+1]['start'] if i+1<len(g) else w['end']+.03
            if end<=w['start']: continue
            line=' '.join((r'{\c&H0000E8FF&}' if j==i else r'{\c&H00FFFFFF&}')+item['text'] for j,item in enumerate(g))
            events.append(f'Dialogue: 0,{stamp(w["start"])},{stamp(end)},Main,,0,0,0,,{{\\pos(360,1000)}}'+line)
    path.write_text(header+'\n'.join(events)+'\n')
    return mapped


results=[]
for edit in EDITS:
    work=OUT/edit['slug']; work.mkdir(exist_ok=True)
    parts=[]; plans=[]
    for a,b,punch in edit['beats']:
        for lo,hi in cuts(a,b):
            plan=crop_plan(lo,hi,punch)
            part=work/f'part-{len(parts):02d}.mp4'
            vf=f"crop={plan['w']}:{plan['h']}:x='{plan['x']}':y={plan['y']},scale=720:1280:flags=lanczos,setsar=1,fps=30"
            run([FFMPEG,'-v','error','-y','-ss',str(lo),'-i',str(SOURCE),'-t',str(hi-lo),'-map','0:v:0','-map','0:a:0','-vf',vf,'-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-ar','48000',str(part)])
            parts.append(part)
            plans.append({'start':lo,'end':hi,'punch':punch,**plan})
    concat=work/'concat.txt'; concat.write_text('\n'.join(f"file '{p}'" for p in parts))
    joined=work/'joined.mp4'
    run([FFMPEG,'-v','error','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(joined)])
    ass=work/'captions.ass'; mapped=captions(edit,ass)
    output=OUT/(edit['slug']+'.mp4')
    run([FFMPEG,'-v','error','-y','-i',str(joined),'-vf',f'subtitles=filename={ass}:fontsdir={ROOT / "backend/fonts"}','-c:v','libx264','-preset','medium','-crf','21','-maxrate','1800k','-bufsize','3600k','-pix_fmt','yuv420p','-af','loudnorm=I=-14:TP=-1.5:LRA=11','-c:a','aac','-b:a','128k','-ar','48000','-movflags','+faststart',str(output)])
    probe=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]).stdout)
    dur=float(probe['format']['duration'])
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    assert (video['width'],video['height'])==(720,1280)
    assert abs(dur-sum(b-a for a,b,_ in edit['beats']))<.4
    decoded=run([FFMPEG,'-v','error','-i',str(output),'-f','null','-'])
    assert not decoded.stderr.strip(),decoded.stderr
    sheet=Image.new('RGB',(1440,675),'#171717'); draw=ImageDraw.Draw(sheet)
    for i,t in enumerate([.6,4.5,dur*.5,dur-1]):
        frame=work/f'qa-{i}.jpg'
        run([FFMPEG,'-v','error','-y','-ss',str(t),'-i',str(output),'-frames:v','1','-vf','scale=360:640',str(frame)])
        sheet.paste(Image.open(frame),(i*360,30)); draw.text((i*360+8,8),f'{t:.2f}s',fill='white')
    sheet.save(OUT/(edit['slug']+'-review.jpg'))
    result={'title':edit['title'],'path':str(output),'duration':dur,'bytes':output.stat().st_size,'beats':edit['beats'],'crop_plans':plans,'transcript':' '.join(w['text'] for w in mapped),'full_decode':'passed'}
    results.append(result)
    (OUT/'manifest.json').write_text(json.dumps(results,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='crop_plans'}),flush=True)
assert len(results)==3
