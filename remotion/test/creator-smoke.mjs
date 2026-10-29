// Explicit opt-in integration smoke: node test/creator-smoke.mjs. No network or installs.
import {mkdtemp,writeFile,readFile,readdir} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {renderCreator} from '../render-creator.mjs';
const root=path.resolve(import.meta.dirname,'../..');
const temp=await mkdtemp(path.join(os.tmpdir(),'creator-smoke-'));
for(const preset of ['clean-energy','aggressive']) {
  const job={outputDir:path.join(temp,preset),fontPath:path.join(root,'backend/fonts/Poppins-ExtraBold.ttf'),width:360,height:640,fps:preset==='clean-energy'?30:24,durationInFrames:12,preset,words:[{text:'Actual',start:.04,end:.15},{text:'audition!',start:.15,end:.32,emphasis:true}],headline:{text:'The audition',start:.04,end:.32},labels:[{text:'Wait...',x:.5,y:.4,start:.04,end:.32}],callouts:[{type:'arrow',x:.2,y:.3,toX:.4,toY:.4,start:.04,end:.32},{type:'circle',x:.65,y:.4,radius:.08,start:.04,end:.32}],counter:{start:.04,end:.32,from:0,to:3,x:.5,y:.5,label:'Take'},progress:{start:.04,end:.32}};
  const file=path.join(temp,`${preset}.json`);await writeFile(file,JSON.stringify(job));
  const m=await renderCreator(file);
  assert.equal(m.frameCount,12);assert.equal((await readdir(job.outputDir)).filter(f=>f.endsWith('.png')).length,12);
  assert.deepEqual(JSON.parse(await readFile(path.join(job.outputDir,'manifest.json'),'utf8')),m);
  await assert.rejects(()=>renderCreator(file),/fresh/);
  const check=spawnSync(process.env.SMOKE_PYTHON??'python3',['-c',`
import json,sys
from pathlib import Path
from PIL import Image
files=sorted(Path(sys.argv[1]).glob('*.png'))
assert len(files)==12
visible=0
for f in files:
    im=Image.open(f)
    assert im.size==(360,640),im.size
    assert im.mode=='RGBA',im.mode
    alpha=im.getchannel('A')
    assert alpha.getpixel((0,0))==0
    assert alpha.getpixel((359,639))==0
    assert alpha.getextrema()[0]==0
    visible+=alpha.getextrema()[1]>0
assert Image.open(files[0]).getchannel('A').getextrema()==(0,0)
assert Image.open(files[-1]).getchannel('A').getextrema()==(0,0)
assert visible>0
print(json.dumps({'pngs':len(files),'mode':'RGBA','transparent_first_last':True,'visible_frames':visible}))
`,job.outputDir],{encoding:'utf8'});
  assert.equal(check.status,0,check.stderr);
  console.log(JSON.stringify({preset,manifest:path.join(job.outputDir,'manifest.json'),ffmpegPattern:m.ffmpegPattern,alpha:JSON.parse(check.stdout)}));
}
console.log(`Smoke artifacts retained: ${temp}`);
