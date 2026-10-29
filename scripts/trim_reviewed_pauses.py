"""Shorten ONLY reviewed pauses in an existing clip, keeping all layers in sync.

Example: python scripts/trim_reviewed_pauses.py input.mp4 --remove 3.2:4.1 8.4:9.0 --output-dir /absolute/fresh-dir
Ranges are seconds to remove from the existing edited timeline (not archive time).
Review speech and visual reactions first. This is NOT an automatic silence classifier.
"""
import argparse,json,math,subprocess
from fractions import Fraction
from pathlib import Path

def run(cmd):
 r=subprocess.run([str(x) for x in cmd],capture_output=True,check=True);return r.stdout

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('--remove',nargs='+',required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
 src=a.input.expanduser().resolve(strict=True);out=a.output_dir.expanduser().resolve()
 if src==out or out in src.parents:p.error('Output cannot contain source')
 info=json.loads(run(['ffprobe','-v','error','-show_streams','-of','json',src]));v=next(s for s in info['streams'] if s['codec_type']=='video');audio=next(s for s in info['streams'] if s['codec_type']=='audio');fps=Fraction(v['avg_frame_rate'])
 if fps!=Fraction(v['r_frame_rate']):p.error('Normalize variable-frame-rate sources before cutting')
 n=int(v.get('nb_frames') or round(float(v['duration'])*fps));cuts=[]
 for item in a.remove:
  try:x,y=map(float,item.split(':'))
  except ValueError:p.error('Use start:end seconds')
  if not math.isfinite(x+y) or not 0<=x<y:p.error('Invalid removal range')
  start=math.ceil(x*fps);end=math.floor(y*fps)
  if not 0<=start<end<=n:p.error('Removal range must contain at least one in-source frame')
  cuts.append((start,end))
 cuts.sort()
 if any(cuts[i][1]>cuts[i+1][0] for i in range(len(cuts)-1)):p.error('Removal ranges overlap')
 keeps=[];cursor=0
 for start,end in cuts:
  if start>cursor:keeps.append((cursor,start))
  cursor=end
 if cursor<n:keeps.append((cursor,n))
 if not keeps:p.error('Cannot remove entire clip')
 frames=sum(e-s for s,e in keeps);out.mkdir(parents=True,exist_ok=False);filters=[f'[0:v]split={len(keeps)}'+''.join(f'[v{i}]' for i in range(len(keeps))),f'[0:a]asplit={len(keeps)}'+''.join(f'[a{i}]' for i in range(len(keeps)))]
 for i,(start,end) in enumerate(keeps):filters.extend([f'[v{i}]trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS[vc{i}]',f'[a{i}]atrim=start={float(start/fps)}:end={float(end/fps)},asetpts=PTS-STARTPTS[ac{i}]'])
 filters.append(''.join(f'[vc{i}][ac{i}]' for i in range(len(keeps)))+f'concat=n={len(keeps)}:v=1:a=1[v][a]');(out/'filtergraph.txt').write_text(';'.join(filters))
 plan={'source':str(src),'fps':str(fps),'removedFrames':cuts,'keepFrames':keeps,'outputFrames':frames,'secondsRemoved':float((n-frames)/fps),'speedChange':False,'visualReview':'pending','deliveryReady':False};(out/'edit-plan.json').write_text(json.dumps(plan,indent=2))
 final=out/'final.mp4';run(['ffmpeg','-v','error','-n','-threads','2','-i',src,'-filter_complex_threads','1','-filter_complex_script',out/'filtergraph.txt','-map','[v]','-map','[a]','-r',str(fps),'-fps_mode','cfr','-c:v','libx264','-threads','2','-preset','fast','-crf','21','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',final]);run(['ffmpeg','-v','error','-xerror','-i',final,'-f','null','-'])
 checked=json.loads(run(['ffprobe','-v','error','-show_streams','-of','json',final]));video=next(s for s in checked['streams'] if s['codec_type']=='video');sound=next(s for s in checked['streams'] if s['codec_type']=='audio')
 if int(video['nb_frames'])!=frames or abs(float(video['duration'])-float(sound['duration']))>.06:raise RuntimeError('Output timing verification failed')
 plan.update(fullDecode='passed',frameCountMatches=True,outputSeconds=float(video['duration']));(out/'qa.json').write_text(json.dumps(plan,indent=2));print(json.dumps(plan,indent=2))
if __name__=='__main__':main()
