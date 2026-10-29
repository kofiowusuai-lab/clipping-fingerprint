"""Render a deliberate second treatment using the SAME prepared picture/audio."""
import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs/premium-dana';W=O/'renders/01-time-freedom';A=O/'renders/01-time-freedom-clean';A.mkdir(exist_ok=True)
c=json.loads((O/'pipeline.json').read_text());clip=c['clips'][0];info=json.loads((W/'prepare.json').read_text());preset=json.loads((R/'configs/visuals/podcast-clean.json').read_text());preset.pop('description',None)
job={'videoPath':str(W/'picture.mp4'),'outputPath':str(A/'graphics.mp4'),'fontPath':c['fontPath'],'fps':c['fps'],'durationInFrames':info['frames'],'width':c['width'],'height':c['height'],'words':json.loads((W/'words.json').read_text()),'headline':clip['headline'],'headlineDuration':clip['captions']['headlineDuration'],'strikeWords':clip['captions']['strikeWords'],**preset,'transitions':clip['renderOptions']['transitions'],'renderOptions':{'crf':18,'muted':True,'audioBitrate':'192k'}}
(A/'render.job.json').write_text(json.dumps(job,indent=2));subprocess.run(['node',str(R/'remotion/render.mjs'),str(A/'render.job.json')],check=True)
subprocess.run(['ffmpeg','-v','error','-y','-i',str(A/'graphics.mp4'),'-i',str(W/'normalized.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(A/'final.mp4')],check=True)
sys.path.insert(0,str(R/'scripts'));import podcast_pipeline as pipeline
(A/'prepare.json').write_text((W/'prepare.json').read_text());(A/'post-caption.txt').write_text(clip['postCaption']+'\n');pipeline.qa(c,clip,A)
(A/'comparison-intent.json').write_text(json.dumps({'base':str(W/'final.mp4'),'alternate':str(A/'final.mp4'),'fixed':['picture preparation','audio preparation','hook wording and duration','riser and white flash','word timing','font file','font size ratios','caption location','red inline strikes','post caption'],'changed':['caption casing','yellow to cyan accent','caption entrance scale removed'],'notAnAudienceTest':True},indent=2));print('Alternative rendered and technical QA complete; visual review pending',flush=True)
