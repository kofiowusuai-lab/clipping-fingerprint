"""Rebuild DDG picture/audio at native 30fps; reuse verified caption graphics only."""
import json, math, shutil, subprocess, sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from creator_engine import run,normalized_audio,qa,save
O=R/'outputs/creator-engine/Vpd-xFMfCq0'
c=json.loads((O/'clip-plan.json').read_text());old=Path(c['outputDir'])/'clean-energy'
w=O/'sync-zoom-persistent-hero';w.mkdir(exist_ok=True)
oldstart=c['start']; c.update(start=24.1,fps=30,outputDir=str(w));n=round((c['end']-c['start'])*30);duration=n/30;c['end']=c['start']+duration
shift=c['start']-oldstart
for word in c['words']:
    word['start']=max(0,word['start']-shift);word['end']=min(duration,word['end']-shift)
c['graphics']['headline'].update(start=0,end=duration)
# Full hero is retained, while the original upper graphics band is cleared from captions.
hero=Image.new('RGBA',(1080,1920));frame=Image.open(sorted((old/'graphics').glob('frame-*.png'))[24]).convert('RGBA');hero.paste(frame.crop((0,0,1080,460)),(0,0));hero.save(w/'hero.png')
# Boundaries are explicit output-frame positions. Wide segments protect unlock/hand action.
beats=[(0,4,300,650,1.0,1.12,'Opening cheating-got-harder hook'),(4,14.5,300,650,1.12,1.12,'Touch ID explanation'),(14.5,20.5,300,650,1.12,1.0,'Pull out for disclaimer and demonstration'),(20.5,30.7,300,650,1.0,1.0,'Preserve complete phone unlock action'),(30.7,34.3,100,800,1.0,1.10,'First gloves recommendation; wider left margin for physical lean'),(34.3,40.0,100,800,1.10,1.0,'Pull out for leftward physical lean'),(40.0,48.5,300,650,1.0,1.08,'Drunk-night scenario builds'),(48.5,54.8,300,650,1.08,1.0,'Pull out for finger demonstration'),(54.8,60.7,300,650,1.0,1.15,'Punch in for slap/crying payoff'),(60.7,duration,300,650,1.15,1.0,'Ease back out on closing')]
shots=[];cursor=0
for i,(a,b,x,cw,z0,z1,reason) in enumerate(beats):
    stop=n if i==len(beats)-1 else round(b*30)
    shots.append(dict(startFrame=cursor,endFrame=stop,crop=[x,120,cw,600],zoomStart=z0,zoomEnd=z1,reviewed=True,reason=reason));cursor=stop
c['shots']=shots;save(w/'edit-plan.json',c)
normalized_audio(c,w,n)
g=[f'[0:v]trim=end_frame={n},settb=1/30,setpts=N/(30*TB),split={len(shots)}'+''.join(f'[s{i}]' for i in range(len(shots)))]
for i,s in enumerate(shots):
    x,y,cw,ch=s['crop'];fh=round(1080*ch/cw)//2*2;top=(1920-fh)//2;count=s['endFrame']-s['startFrame']
    # Smoothstep performs actual in/out motion, never varying frame rate or audio speed.
    progress=f'min(on/{max(1,count-1)},1)';e=f'({progress})*({progress})*(3-2*({progress}))';z=f"{s['zoomStart']}+({s['zoomEnd']}-{s['zoomStart']})*({e})"
    g.append(f'[s{i}]trim=start_frame={s["startFrame"]}:end_frame={s["endFrame"]},setpts=PTS-STARTPTS,split=2[b{i}][f{i}]')
    g.append(f'[b{i}]scale=180:320:force_original_aspect_ratio=increase,crop=180:320,boxblur=8:1,eq=brightness=-0.10:saturation=0.65,scale=1080:1920:flags=bilinear[bg{i}]')
    g.append(f"[f{i}]crop={cw}:{ch}:{x}:{y},scale=1080:{fh}:flags=lanczos,setsar=1,zoompan=z='{z}':x='iw/2-iw/(2*zoom)':y='ih*0.35-ih*0.35/zoom':d=1:s=1080x{fh}:fps=30[fg{i}]")
    g.append(f'[bg{i}][fg{i}]overlay=0:{top}:shortest=1,setsar=1[v{i}]')
g.append(''.join(f'[v{i}]' for i in range(len(shots)))+f'concat=n={len(shots)}:v=1:a=0,fps=30,settb=1/30,setpts=N/(30*TB),tpad=stop_mode=clone:stop_duration=0.1,trim=end_frame={n}[picture]')
g.append(f'[1:v]format=rgba,crop=1080:1460:0:460,pad=1080:1920:0:460:color=black@0,setpts=PTS-STARTPTS-{shift}/TB[captions]')
g.append('[picture][captions]overlay=0:0:eof_action=repeat:shortest=0:format=auto[captioned]')
g.append('[captioned][3:v]overlay=0:0:eof_action=repeat:shortest=0:format=auto,format=yuv420p[v]')
(w/'filtergraph.txt').write_text(';'.join(g))
# Native source picture and PCM audio use the exact same frame-boundary start.
run(['ffmpeg','-v','error','-y','-threads','2','-ss',c['start'],'-i',c['source'],'-framerate','24','-pattern_type','glob','-i',str(old/'graphics/*.png'),'-i',w/'normalized.wav','-loop','1','-framerate','30','-i',w/'hero.png','-filter_complex_threads','1','-filter_complex_script',w/'filtergraph.txt','-map','[v]','-map','2:a:0','-frames:v',n,'-r','30','-fps_mode','cfr','-c:v','libx264','-threads','2','-preset','fast','-crf','23','-maxrate','1600k','-bufsize','3200k','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',w/'final.mp4'])
report=qa(c,w,n,w/'final.mp4');report['graphicsReuse']={'source':str(old/'graphics'),'captionTimeShiftSeconds':shift,'hero':'Static fully visible layer throughout output; old upper band cleared'};report['syncMethod']='Picture and PCM audio cut together from native 30fps source at exactly24.1s; no arbitrary audio delay applied.';save(w/'qa.json',report)
(w/'post-caption.txt').write_text(c['postCaption']+'\n');print(json.dumps(report,indent=2))
