"""Compose a reviewed creator batch plan with a fast Remotion caption band."""
import argparse,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from creator_engine import run,normalized_audio,qa,save
p=argparse.ArgumentParser();p.add_argument('plan',type=Path);args=p.parse_args();c=json.loads(args.plan.read_text());w=args.plan.parent;n=c['durationInFrames'];fps=c['fps'];segments=c['segments'];assert fps==30
m=json.loads((w/'graphics/manifest.json').read_text());assert m['frameCount']==n and m['fps']==fps
# PCM audio edits share native frame boundaries with the picture edits.
ranges=c['archiveRanges'];ag=[]
if len(ranges)>1:ag.append(f'[0:a]asplit={len(ranges)}'+''.join(f'[a{i}]' for i in range(len(ranges))))
for i,(a,b) in enumerate(ranges):
    source=f'[a{i}]' if len(ranges)>1 else '[0:a]';ag.append(f'{source}atrim=start={a-c["archiveOffset"]}:end={b-c["archiveOffset"]},asetpts=PTS-STARTPTS[cut{i}]')
ag.append(''.join(f'[cut{i}]' for i in range(len(ranges)))+f'concat=n={len(ranges)}:v=0:a=1[a]')
run(['ffmpeg','-v','error','-y','-i',c['source'],'-filter_complex',';'.join(ag),'-map','[a]','-ar','48000','-ac','2','-c:a','pcm_s24le',w/'speech-cut.wav'])
normalized_audio({'source':str(w/'speech-cut.wav'),'start':0,'fps':fps},w,n)
g=[f'[0:v]split={len(segments)}'+''.join(f'[s{i}]' for i in range(len(segments)))]
for i,s in enumerate(segments):
    count=s['endFrame']-s['startFrame'];start=round(s['sourceStart']*fps);stop=start+count;x,y,cw,ch=s['crop'];fh=round(1080*ch/cw)//2*2;top=460 if s['tweetPanel'] else (1920-fh)//2
    z0,z1=s['zoomStart'],s['zoomEnd'];u=f'min(on/{max(1,count-1)},1)';ease=f'({u})*({u})*(3-2*({u}))';z=f'{z0}+({z1}-{z0})*({ease})'
    tags=f'[b{i}][f{i}][t{i}]' if s['tweetPanel'] else f'[b{i}][f{i}]'
    g.append(f'[s{i}]trim=start_frame={start}:end_frame={stop},setpts=PTS-STARTPTS,split={3 if s["tweetPanel"] else 2}'+tags)
    g.append(f'[b{i}]scale=180:320:force_original_aspect_ratio=increase,crop=180:320,boxblur=8:1,eq=brightness=-0.10:saturation=0.65,scale=1080:1920:flags=bilinear[bg{i}]')
    g.append(f"[f{i}]crop={cw}:{ch}:{x}:{y},scale=1080:{fh}:flags=lanczos,setsar=1,zoompan=z='{z}':x='iw/2-iw/(2*zoom)':y='ih*0.35-ih*0.35/zoom':d=1:s=1080x{fh}:fps=30[fg{i}]")
    g.append(f'[bg{i}][fg{i}]overlay=0:{top}:shortest=1,setsar=1'+(f'[pre{i}]' if s['tweetPanel'] else f'[v{i}]'))
    if s['tweetPanel']:
        g.append(f'[t{i}]crop=398:66:424:292,scale=1080:180:flags=lanczos[tw{i}]');g.append(f'[pre{i}][tw{i}]overlay=0:1250:shortest=1[v{i}]')
g.append(''.join(f'[v{i}]' for i in range(len(segments)))+f'concat=n={len(segments)}:v=1:a=0,fps=30,settb=1/30,setpts=N/(30*TB),tpad=stop_mode=clone:stop_duration=0.1,trim=end_frame={n}[picture]')
g.append(f'[picture][1:v]overlay=0:{m["bandTop"]}:eof_action=repeat:shortest=0:format=auto[captioned]')
g.append('[captioned][3:v]overlay=0:0:eof_action=repeat:shortest=0:format=auto,format=yuv420p[v]')
(w/'filtergraph.txt').write_text(';'.join(g))
run(['ffmpeg','-v','error','-y','-threads','2','-i',c['source'],'-framerate','30','-i',m['ffmpegPattern'],'-i',w/'normalized.wav','-loop','1','-framerate','30','-i',m['heroPath'],'-filter_complex_threads','1','-filter_complex_script',w/'filtergraph.txt','-map','[v]','-map','2:a:0','-frames:v',n,'-r','30','-fps_mode','cfr','-c:v','libx264','-threads','2','-preset','fast','-crf','23','-maxrate','1400k','-bufsize','2800k','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',w/'final.mp4'])
report=qa({'width':1080,'height':1920,'fps':30,'shots':segments},w,n,w/'final.mp4');report.update(nativeFrameRate=True,captionMode='One word at a time with pop-in',persistentHero=True,graphicsManifest=str(w/'graphics/manifest.json'),limitations=c['limitations']);save(w/'qa.json',report);print(json.dumps(report,indent=2))
