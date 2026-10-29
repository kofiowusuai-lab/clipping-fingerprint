import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validateJob} from '../schema.mjs';
const job=()=>({videoPath:'/clip.mp4',outputPath:'/out.mp4',fontPath:'/font.ttf',style:'clean',headline:'',headlineDuration:3,width:720,height:1280,fps:30,durationInFrames:90,words:[{text:'Hello',start:0,end:1}]});
test('accepts valid second-based timeline',()=>assert.equal(validateJob(job()).fps,30));
test('rejects milliseconds and words past the end',()=>{let j=job();j.words[0].end=1000;assert.throws(()=>validateJob(j));});
test('rejects unsorted/overlapping captions',()=>{let j=job();j.words.push({text:'world',start:.5,end:2});assert.throws(()=>validateJob(j));});
test('rejects negative timestamps',()=>{let j=job();j.words[0].start=-1;assert.throws(()=>validateJob(j));});
test('rejects missing input',()=>{let j=job();delete j.videoPath;assert.throws(()=>validateJob(j));});
test('rejects unsupported style',()=>{let j=job();j.style='random';assert.throws(()=>validateJob(j));});
test('rejects odd H264 dimensions',()=>{let j=job();j.width=721;assert.throws(()=>validateJob(j));});
test('accepts bold style and no captions',()=>{let j=job();j.style='bold';j.words=[];assert.equal(validateJob(j).style,'bold');});

test('accepts a valid headline accent',()=>{let j=job();j.headlineAccent='#00E5FF';assert.equal(validateJob(j).headlineAccent,'#00E5FF');});
test('rejects invalid headline accent',()=>{let j=job();j.headlineAccent='red;background:black';assert.throws(()=>validateJob(j));});

test('accepts a partial intro render',()=>{let j=job();j.frameRange=[0,29];assert.equal(validateJob(j).frameRange[1],29);});
test('rejects invalid render ranges',()=>{for(const range of [[-1,2],[5,1],[0,90],[0,1.5]]){let j=job();j.frameRange=range;assert.throws(()=>validateJob(j));}});

test('accepts three strike-through words',()=>{let j=job();j.strikeWords=['birthdays','Christmas','Thanksgivings'];assert.equal(validateJob(j).strikeWords.length,3);});
test('rejects invalid strike-through lists',()=>{for(const words of [[''],Array(101).fill('one'),[5],'no']){let j=job();j.strikeWords=words;assert.throws(()=>validateJob(j));}});
