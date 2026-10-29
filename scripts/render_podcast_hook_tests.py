"""Controlled four-hook x two-headline-colour test exports of the locked edit."""
import argparse,csv,json,subprocess,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];O=R/'outputs/podcast-hook-tests';O.mkdir(exist_ok=True)
BASE=R/'outputs/remotion-corrected';VIDEO=BASE/'prepared-full.mp4';WORDS=BASE/'words.json'
HOOKS={
 'A':{'text':'WANT MORE\nFREE TIME? DON’T\nSTART A BUSINESS.','hypothesis':'Contradiction: business ownership versus wanting more free time.'},
 'B':{'text':'BE YOUR OWN BOSS.\nLOSE YOUR\nFREE TIME.','hypothesis':'Direct personal trade-off of becoming your own boss.'},
 'C':{'text':'STARTING A\nBUSINESS?\nFORGET DAYS OFF.','hypothesis':'Directly address aspiring founders and expose the cost.'},
 'D':{'text':'NO BIRTHDAYS.\nNO CHRISTMAS.\nNO DAYS OFF.','hypothesis':'Concrete personal stakes from the spoken passage rather than an abstract promise.'},
}
COLOURS={'yellow':'#FFE000','cyan':'#00E5FF'}
COPY="Starting a business for more freedom? Be prepared to have less of it first.\n\nDana White on the reality behind being your own boss.\n\nWhat surprised you most about working for yourself?\n\n#DanaWhite #Entrepreneurship #BusinessOwner #FounderLife #BusinessReality"
expected={f'{h}-{c}' for h in HOOKS for c in COLOURS}
p=argparse.ArgumentParser();p.add_argument('--only',help='Comma-separated variant IDs');a=p.parse_args();selected=set(a.only.split(',')) if a.only else expected
assert selected<=expected
font=ImageFont.truetype(str(R/'backend/fonts/Poppins-ExtraBold.ttf'),54)
for h in HOOKS.values():
 for line in h['text'].splitlines():assert font.getlength(line)<=720*.86,(line,font.getlength(line))
manifest=json.loads((O/'manifest.json').read_text()) if (O/'manifest.json').exists() else []
(O/'design.json').write_text(json.dumps({'hooks':HOOKS,'headline_colours':COLOURS,'headline_seconds':3,'unchanged':['video','spoken hook','body','captions','caption accent','font','font sizes','audio','riser','flash','duration','post copy'],'post_copy':COPY,'status':'exports only; no audience test or publishing performed'},indent=2))

def run(cmd,log):
 with log.open('w') as f:subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT,check=True)

def ahash(path):
 return subprocess.run(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-c','copy','-f','hash','-hash','sha256','-'],check=True,capture_output=True,text=True).stdout.strip()

# Only the first 90 frames differ. Reuse the already-checked common body and
# an identical approved AAC packet stream, instead of rerendering it eight times.
body=O/'common-body.mp4'
if not body.exists() or json.loads(subprocess.run(['ffprobe','-v','error','-show_entries','stream=nb_frames','-of','json',str(body)],check=True,capture_output=True,text=True).stdout)['streams'][0]['nb_frames']!='520':
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(BASE/'captioned-full.mp4'),'-an','-vf','trim=start_frame=90,setpts=PTS-STARTPTS,fps=30','-r','30','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',str(body)],check=True)
audio_reference=O/'A-yellow.mp4'
assert audio_reference.exists(), 'Render and verify A-yellow once before optimized variants'
template=json.loads((O/'A-yellow/captioned.job.json').read_text())
for letter,hook in HOOKS.items():
 for colour,hexcode in COLOURS.items():
  vid=f'{letter}-{colour}'
  if vid not in selected:continue
  work=O/vid;work.mkdir(exist_ok=True);base=work/'captioned.mp4';final=O/(vid+'.mp4')
  if any(m['id']==vid for m in manifest):
   print('Already verified: '+vid,flush=True);continue
  intro=work/'intro.mp4';job={**template,'outputPath':str(intro),'headline':hook['text'],'headlineAccent':hexcode,'frameRange':[0,89]}
  jobfile=work/'intro.job.json'
  cached=intro.exists() and jobfile.exists() and json.loads(jobfile.read_text())==job
  if cached:
   check=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_type,nb_frames','-of','json',str(intro)],capture_output=True,text=True)
   try:cached=check.returncode==0 and next(s for s in json.loads(check.stdout)['streams'] if s['codec_type']=='video')['nb_frames']=='90'
   except (ValueError,KeyError,StopIteration):cached=False
  jobfile.write_text(json.dumps(job,indent=2))
  if not cached:
   with (work/'render.log').open('w') as f:subprocess.run(['node','render.mjs',str(jobfile)],cwd=R/'remotion',stdout=f,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['ffmpeg','-v','error','-y','-i',str(intro),'-i',str(body),'-i',str(audio_reference),'-filter_complex','[0:v]setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1:a=0[v]','-map','[v]','-map','2:a:0','-r','30','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(base)],check=True)
  run([sys.executable,str(R/'scripts/check_remotion_frames.py'),str(VIDEO),str(base),'--report',str(work/'captioned-frame-check.json')],work/'frame-check.log')
  run([sys.executable,str(R/'scripts/add_white_luma_flash.py'),'--source',str(base),'--output-dir',str(work),'--output-name',str(final),'--cut-seconds','7.9'],work/'flash.log')
  run([sys.executable,str(R/'scripts/check_remotion_frames.py'),str(VIDEO),str(final),'--report',str(work/'final-frame-check.json'),'--skip-frame-start','234','--skip-frame-end','245'],work/'final-frame-check.log')
  proof=json.loads((work/'verification.json').read_text());assert proof['frames']==610
  digest=ahash(final)
  if manifest:assert digest==manifest[0]['audio_packet_hash'],'Audio differed between test cells'
  jpg=work/'hero-review.jpg';subprocess.run(['ffmpeg','-v','error','-y','-ss','1.5','-i',str(final),'-frames:v','1',str(jpg)],check=True)
  record={'id':vid,'hook':letter,'headline':hook['text'],'headline_colour':colour,'hex':hexcode,'path':str(final),'duration':float(proof['duration']),'frames':proof['frames'],'full_decode':proof['full_decode'],'frame_checks':'passed','audio_packet_hash':digest,'post_copy':COPY,'audience_test_status':'not run'}
  manifest=[m for m in manifest if m['id']!=vid]+[record];manifest.sort(key=lambda m:m['id']);(O/'manifest.json').write_text(json.dumps(manifest,indent=2))
  print(json.dumps({k:record[k] for k in ['id','path','duration','frame_checks']}),flush=True)

# Durable metrics template: no invented impressions, retention or winning cell.
with (O/'results-template.csv').open('w',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=['variant','platform','post_url','observation_window','impressions_or_starts','three_second_views','average_watch_seconds','completion_rate','shares','saves','notes']);writer.writeheader()
 for item in sorted(expected):writer.writerow({'variant':item})
(O/'post-caption.txt').write_text(COPY+'\n')
if set(m['id'] for m in manifest)==expected:
 sheet=Image.new('RGB',(1440,4*665),'#202020');d=ImageDraw.Draw(sheet)
 for i,m in enumerate(manifest):
  im=Image.open(O/m['id']/'hero-review.jpg');im.thumbnail((360,640));x=i%4*360;y=i//4*665;sheet.paste(im,(x,y+25));d.text((x+8,y+5),m['id'],fill='white')
 # Four columns, two rows = all eight hero variants.
 sheet=sheet.crop((0,0,1440,2*665));sheet.save(O/'all-heroes.jpg')
 assert len(manifest)==8 and len({m['path'] for m in manifest})==8
 print('ALL EIGHT VERIFIED',flush=True)
