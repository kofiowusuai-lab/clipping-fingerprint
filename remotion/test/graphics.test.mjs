import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validateJob} from '../schema.mjs';
const base=()=>({videoPath:'/clip.mp4',outputPath:'/out.mp4',fontPath:'/font.ttf',style:'bold',headline:'',headlineDuration:3,width:720,height:1280,fps:30,durationInFrames:90,words:[]});
const graphics=()=>({...base(),captionStyle:{fontSizeRatio:.095,position:{bottomRatio:.19,sidesRatio:.065},maxWords:3,maxChars:21,color:'#ffffff',activeColor:'#ffe000',strokeColor:'#000000',strokeWidth:1,shadow:{color:'#000000',blur:5,offsetX:0,offsetY:2},entrance:{scale:.97,translateY:10,duration:.15},keywords:{hello:{scale:1.1,color:'#00ffff',offsetY:-4}}},headlineStyle:{topRatio:.075,fontSizeRatio:.075,color:'#ffffff',accentColor:'#ff0000'},lowerThirds:[{start:0,end:1,name:'Example',title:'Speaker'}],overlays:[{start:1,end:2,imagePath:'/logo.png'}],endcard:{start:2,end:3,text:'End',subtitle:'Example'},background:{color:'#101014',fit:'contain',blur:10},supportingVideo:{videoPath:'/support.mp4',layout:'stacked'},transitions:[{time:1,rise:.1,fall:.3}],renderOptions:{crf:18,audioBitrate:'192k',volume:1,muted:false}});
test('accepts complete optional graphics contract',()=>assert.equal(validateJob(graphics()).endcard.text,'End'));
for(const [name,change] of [
 ['unsafe CSS',j=>j.captionStyle.color='red;display:none'],
 ['arbitrary style key',j=>j.captionStyle.transform='rotate(10deg)'],
 ['nonfinite size',j=>j.captionStyle.fontSizeRatio=Infinity],
 ['excessive font',j=>j.captionStyle.fontSizeRatio=.9],
 ['bad group count',j=>j.captionStyle.maxWords=2.5],
 ['unsafe keyword scale',j=>j.captionStyle.keywords.hello.scale=10],
 ['unsafe shadow',j=>j.captionStyle.shadow.blur=-2],
 ['bad headline',j=>j.headlineStyle.topRatio=NaN],
 ['reversed interval',j=>j.lowerThirds[0].end=0],
 ['outside clip',j=>j.endcard.end=4],
 ['network image',j=>j.overlays[0].imagePath='https://example.com/a.png'],
 ['SVG disallowed',j=>j.overlays[0].imagePath='/logo.svg'],
 ['relative media',j=>j.videoPath='../clip.mp4'],
 ['ambiguous overlay',j=>j.overlays[0].text='both'],
 ['negative blur',j=>j.background.blur=-1],
 ['bad fit',j=>j.background.fit='fill'],
 ['transition outside duration',j=>j.transitions[0].time=0],
 ['bad layout',j=>j.supportingVideo.layout='random'],
 ['CRF out of range',j=>j.renderOptions.crf=52],
 ['audio injection',j=>j.renderOptions.audioBitrate='128k -f wav'],
 ['invalid volume',j=>j.renderOptions.volume=-1],
 ['negative word edge',j=>j.words=[{text:'bad',start:-.0001,end:1}]],
]) test(`rejects ${name}`,()=>{const j=graphics();change(j);assert.throws(()=>validateJob(j));});
