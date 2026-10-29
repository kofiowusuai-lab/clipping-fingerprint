"""Render the requested holiday strike graphic in A-yellow, preserving its audio/intro."""
import json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs/podcast-strikethrough';O.mkdir(exist_ok=True)
SRC=R/'outputs/podcast-hook-tests/A-yellow.mp4';SEG=O/'holiday-segment.mp4';FINAL=O/'A-yellow-holiday-strikes.mp4'
job=json.loads((R/'outputs/podcast-hook-tests/A-yellow/captioned.job.json').read_text())
job.update({'outputPath':str(SEG),'frameRange':[246,353],'strikeWords':['birthdays','Christmas','Thanksgivings']})
(O/'job.json').write_text(json.dumps(job,indent=2))
with (O/'render.log').open('w') as f:subprocess.run(['node','render.mjs',str(O/'job.json')],cwd=R/'remotion',stdout=f,stderr=subprocess.STDOUT,check=True)
# Reuse the exact approved intro/flash/body outside the changed graphic window.
graph='[0:v]trim=end_frame=246,setpts=PTS-STARTPTS[p];[1:v]setpts=PTS-STARTPTS[m];[0:v]trim=start_frame=354,setpts=PTS-STARTPTS[s];[p][m][s]concat=n=3:v=1:a=0[v]'
subprocess.run(['ffmpeg','-v','error','-y','-i',str(SRC),'-i',str(SEG),'-filter_complex',graph,'-map','[v]','-map','0:a:0','-r','30','-c:v','libx264','-preset','fast','-crf','19','-maxrate','1800k','-bufsize','3600k','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(FINAL)],check=True)
probe=json.loads(subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(FINAL)],check=True,capture_output=True,text=True).stdout)
v=next(s for s in probe['streams'] if s['codec_type']=='video');a=next(s for s in probe['streams'] if s['codec_type']=='audio')
assert v['nb_frames']=='610' and (v['width'],v['height'])==(720,1280)
assert abs(float(v['duration'])-float(a['duration']))<.05
subprocess.run(['ffmpeg','-v','error','-i',str(FINAL),'-f','null','-'],check=True)
def ahash(p):return subprocess.run(['ffmpeg','-v','error','-i',str(p),'-map','0:a:0','-c','copy','-f','hash','-hash','sha256','-'],check=True,capture_output=True,text=True).stdout.strip()
assert ahash(SRC)==ahash(FINAL)
report={'path':str(FINAL),'duration':float(probe['format']['duration']),'frames':610,'full_decode':'passed','audio':'packet-identical to A-yellow','replaced_frames':[246,353],'strike_targets':[w for w in job['words'] if w['text'].lower().strip(',.') in ['birthdays','christmas','thanksgivings']],'stroke_seconds':.22,'colour':'#ff4148','unchanged':['hero A-yellow','font','font sizes','original speech+riser mix','white flash at 7.9s','opening','ending']}
(O/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
