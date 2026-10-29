"""Reviewed thinking-pause trim; cut A/V and existing graphics together."""
import json,math,subprocess
from pathlib import Path
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1]
b=R/'outputs/creator-engine/Vpd-xFMfCq0/five-clip-batch/02-recognised'
src=b/'meme-hero-incognito/delivery.mp4'; out=b/'meme-hero-tightened';out.mkdir(exist_ok=False)
(out/'.task-monitor-id').write_text('tm_1e82ea72')
fps=30;n=1766
# Detected at -38 dB; checked surrounding source words, excluding short breaths.
pauses=[(3.073604,4.262958),(5.457771,6.439292),(12.127125,13.161354),(23.100604,23.780687),(51.103708,51.849667),(52.995583,53.926792)]
cuts=[(math.ceil((a+.10)*fps),math.floor((z-.12)*fps)) for a,z in pauses]
ranges=[];cursor=0
for a,z in cuts:ranges.append((cursor,a));cursor=z
ranges.append((cursor,n));frames=sum(z-a for a,z in ranges)
plan={'input':str(src),'fps':fps,'removedFrames':cuts,'keepFrames':ranges,'inputFrames':n,'outputFrames':frames,'secondsRemoved':(n-frames)/fps,'outputSeconds':frames/fps,'policy':'Only six reviewed thinking pauses shortened; >=100ms tail and >=120ms next-word handle retained. No speed change. Hero, captions, picture and audio cut on same frame boundaries.'}
(out/'edit-plan.json').write_text(json.dumps(plan,indent=2))
g=[f'[0:v]split={len(ranges)}'+''.join(f'[v{i}]' for i in range(len(ranges))),f'[0:a]asplit={len(ranges)}'+''.join(f'[a{i}]' for i in range(len(ranges)))]
for i,(a,z) in enumerate(ranges):
 g.extend([f'[v{i}]trim=start_frame={a}:end_frame={z},setpts=PTS-STARTPTS[vc{i}]',f'[a{i}]atrim=start_sample={a*1600}:end_sample={z*1600},asetpts=PTS-STARTPTS[ac{i}]'])
g.append(''.join(f'[vc{i}][ac{i}]' for i in range(len(ranges)))+f'concat=n={len(ranges)}:v=1:a=1[v][a]')
(out/'filtergraph.txt').write_text(';'.join(g))
subprocess.run(['ffmpeg','-v','error','-n','-threads','2','-i',str(src),'-filter_complex_threads','1','-filter_complex_script',str(out/'filtergraph.txt'),'-map','[v]','-map','[a]','-c:v','libx264','-threads','2','-preset','fast','-crf','22','-maxrate','1500k','-bufsize','3000k','-pix_fmt','yuv420p','-r','30','-fps_mode','cfr','-c:a','aac','-b:a','160k','-movflags','+faststart',str(out/'final.mp4')],check=True)
probe=json.loads(subprocess.run(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(out/'final.mp4')],capture_output=True,text=True,check=True).stdout)
v=next(s for s in probe['streams'] if s['codec_type']=='video');audio=next(s for s in probe['streams'] if s['codec_type']=='audio');assert int(v['nb_read_frames'])==frames;assert (v['width'],v['height'])==(1080,1920);assert abs(float(v['duration'])-float(audio['duration']))<.05
subprocess.run(['ffmpeg','-v','error','-i',str(out/'final.mp4'),'-f','null','-'],check=True)
# Actual-output contact sheet: first, last and before/after every shortened pause.
times=[0.1,frames/fps-.15];c=0
for a,z in ranges[:-1]:c+=(z-a)/fps;times.extend([max(0,c-.1),min(frames/fps-.1,c+.1)])
sheet=Image.new('RGB',(270*4,510*math.ceil(len(times)/4)),(28,28,28));draw=ImageDraw.Draw(sheet)
for i,t in enumerate(times):
 p=out/f'review-{i:02}.jpg';subprocess.run(['ffmpeg','-v','error','-n','-ss',str(t),'-i',str(out/'final.mp4'),'-frames:v','1','-vf','scale=270:480',str(p)],check=True);sheet.paste(Image.open(p),((i%4)*270,(i//4)*510));draw.text(((i%4)*270+5,(i//4)*510+485),f'{t:.3f}s',fill='white')
sheet.save(out/'contact-sheet.jpg')
(out/'qa.json').write_text(json.dumps({'probe':probe,'fullDecode':'passed','frameCountMatches':True,'sameFrameBoundariesAV':True,'visualReview':'pending','editPlan':plan},indent=2))
print(json.dumps(plan,indent=2))
