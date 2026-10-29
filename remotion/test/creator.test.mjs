import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {validateCreatorJob,validateCreatorPaths} from '../creator-schema.mjs';
const font=path.resolve(import.meta.dirname,'../../backend/fonts/Poppins-ExtraBold.ttf');
const base=()=>({outputDir:'/tmp/creator-unused',fontPath:font,durationInFrames:60,words:[{text:'Actually',start:0,end:.3},{text:'funny!',start:.3,end:.7,emphasis:true}]});
test('creator defaults are independent, selective and mobile sized',()=>{
  const j=validateCreatorJob(base());assert.equal(j.width,1080);assert.equal(j.height,1920);assert.equal(j.fps,30);assert.equal(j.caption.fontSizeRatio,.078);assert.equal(j.words[0].emphasis,false);assert.equal(j.words[1].emphasis,true);assert.equal(j.preset,'clean-energy');
  const a=validateCreatorJob({...base(),preset:'aggressive',fps:24});assert.equal(j.caption.maxWords,1);assert.equal(a.caption.maxWords,1);assert.ok(a.caption.fontSizeRatio>j.caption.fontSizeRatio);
});
test('accepts all opt-in graphics and configurable easing',()=>{
  const j=validateCreatorJob({...base(),caption:{position:'bottom',maxWords:2},emphasis:{keywords:['FUNNY!'],easing:'cubic-out',pop:0,translateYRatio:0},headline:{text:'Real audition',start:.1,end:1},labels:[{text:'Wait for it',start:.2,end:1,x:.4,y:.3}],callouts:[{type:'arrow',x:.2,y:.2,toX:.4,toY:.4,start:.3,end:1},{type:'circle',x:.5,y:.4,radius:.1,start:.4,end:1}],counter:{start:0,end:1,to:10,label:'Attempts'},progress:{start:0,end:2}});
  assert.equal(j.caption.position,.72);assert.equal(j.callouts.length,2);assert.equal(j.emphasis.keywords[0],'funny!');assert.equal(j.emphasis.pop,0);
});
test('reject invalid units, finite/range/unknown fields and unordered words',()=>{
  for(const patch of [{counter:false},{progress:false},{headline:false},{fps:25},{width:NaN},{height:Infinity},{durationInFrames:0},{durationInFrames:1.2},{intensity:-.1},{intensity:1.1},{preset:'podcast'},{videoPath:'/tmp/video.mp4'},{fontPath:'font.ttf'},{outputDir:'relative'},{caption:{maxwords:4}},{caption:{maxWords:9}},{caption:{color:'red'}},{caption:{position:.99}},{emphasis:{duration:0}},{words:[{text:'two words',start:0,end:.2}]},{words:[{text:'x',start:0,end:3}]},{words:[{text:'x',start:0,end:.3},{text:'y',start:.2,end:.4}]},{headline:{text:'bad',start:1,end:1}},{callouts:[{type:'arrow',start:0,end:1,x:.2,y:.3,toX:.2,toY:.3}]},{callouts:[{type:'circle',start:0,end:1,x:.07,y:.3,radius:.3}]},{progress:{start:0,end:1,x:.9,width:.8}}]) assert.throws(()=>validateCreatorJob({...base(),...patch}),JSON.stringify(patch));
});
test('path safety refuses existing dirs, aliases, bogus fonts; never cleans output',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'creator-test-'));
  try{
    const fresh=path.join(root,'frames');const job=validateCreatorJob({...base(),outputDir:fresh});
    assert.equal(validateCreatorPaths(job).outputDir,path.join(fs.realpathSync(root),'frames'));
    fs.mkdirSync(fresh);fs.writeFileSync(path.join(fresh,'keep'),'untouched');assert.throws(()=>validateCreatorPaths(job));assert.equal(fs.readFileSync(path.join(fresh,'keep'),'utf8'),'untouched');
    fs.symlinkSync(fresh,path.join(root,'alias'));assert.throws(()=>validateCreatorPaths({...job,outputDir:path.join(root,'alias')}));
    fs.symlinkSync(path.join(root,'nonexistent'),path.join(root,'dangling'));assert.throws(()=>validateCreatorPaths({...job,outputDir:path.join(root,'dangling')}));
    const bad=path.join(root,'bad.ttf');fs.writeFileSync(bad,'not a font');assert.throws(()=>validateCreatorPaths({...job,fontPath:bad,outputDir:path.join(root,'out')}));
    assert.throws(()=>validateCreatorPaths({...job,outputDir:path.join(root,'missing','out')}));
  }finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('graphics entrypoint cannot decode video or force audio',()=>{
  const source=fs.readFileSync(new URL('../src/creator.tsx',import.meta.url),'utf8');
  assert.doesNotMatch(source,/OffthreadVideo|<video|<audio|<Audio|<Video|renderMedia/);
});
