import path from 'node:path';
import {realpathSync,statSync} from 'node:fs';
export const sameAsset = (a,b) => {
  const canonical=p=>{try{return realpathSync(p);}catch{return path.resolve(p);}};
  if(canonical(a)===canonical(b))return true;
  try{const x=statSync(a),y=statSync(b);return x.dev===y.dev&&x.ino===y.ino;}catch{return false;}
};
const fail = (message) => {throw new Error(message);};
const object = (v, name, keys) => {if (!v || typeof v !== 'object' || Array.isArray(v)) fail(`${name} must be an object`); for (const k of Object.keys(v)) if (!keys.includes(k)) fail(`Unknown ${name}.${k}`);};
const number = (v, name, min, max, integer=false) => {if (!Number.isFinite(v) || v<min || v>max || (integer&&!Number.isInteger(v))) fail(`Invalid ${name} (${min}..${max})`);};
const text = (v,name,max=120) => {if(typeof v!=='string'||!v.trim()||v.length>max) fail(`Invalid ${name}`);};
const color = (v,name) => {if(typeof v!=='string'||!/^#[\da-f]{6}$/i.test(v)) fail(`${name} must be a six-digit hex colour`);};
export const validateAssetPath = (v, extensions) => {if(typeof v!=='string'||!path.isAbsolute(v)||v.includes('\0')||!extensions.includes(path.extname(v).toLowerCase())) fail('Assets must be absolute local paths with permitted extensions');};
const image = v => validateAssetPath(v,['.png','.jpg','.jpeg','.webp']);
const optional = (o,k,fn) => {if(o[k]!==undefined) fn(o[k],k);};
function graphic(o,name,duration,keys=[]) {
  object(o,name,['start','end','xRatio','yRatio','widthRatio','fontSizeRatio','color','backgroundColor',...keys]);
  optional(o,'entranceDuration',v=>number(v,'entranceDuration',0,2));
  number(o.start,`${name}.start`,0,duration); number(o.end,`${name}.end`,0,duration); if(o.end<=o.start) fail('Graphic end must follow start');
  for(const k of ['xRatio','yRatio']) optional(o,k,(v)=>number(v,k,0,1));
  optional(o,'widthRatio',v=>number(v,'widthRatio',.05,1)); optional(o,'fontSizeRatio',v=>number(v,'fontSizeRatio',.01,.2));
  for(const k of ['color','backgroundColor']) optional(o,k,color);
}
export function validateJob(job) {
  if (!job || typeof job !== 'object' || Array.isArray(job)) fail('Job must be an object');
  for (const key of ['videoPath','outputPath','fontPath']) if(typeof job[key]!=='string'||!job[key]) fail(`${key} is required`);
  validateAssetPath(job.videoPath,['.mp4','.mov','.webm','.mkv']); validateAssetPath(job.fontPath,['.ttf','.otf','.woff','.woff2']);
  for(const key of ['fps','durationInFrames','width','height']) number(job[key],key,1,({fps:120,durationInFrames:216000,width:7680,height:7680})[key],true);
  if(job.width%2||job.height%2) fail('H264 dimensions must be even');
  if(!['clean','bold'].includes(job.style)) fail('Unknown caption style');
  if(typeof job.headline!=='string'||job.headline.length>120) fail('headline must be a string of at most 120 characters');
  optional(job,'headlineAccent',color); number(job.headlineDuration,'headlineDuration',0,7200);
  if(job.frameRange!==undefined && (!Array.isArray(job.frameRange)||job.frameRange.length!==2||!job.frameRange.every(Number.isInteger)||job.frameRange[0]<0||job.frameRange[1]<job.frameRange[0]||job.frameRange[1]>=job.durationInFrames)) fail('Invalid frameRange');
  if(job.strikeWords!==undefined && (!Array.isArray(job.strikeWords)||job.strikeWords.length>100||job.strikeWords.some(w=>typeof w!=='string'||!w.trim()||w.length>40))) fail('strikeWords must contain up to 100 nonempty words of at most 40 characters');
  if(!Array.isArray(job.words)) fail('words must be an array');
  let lastEnd=0; const duration=job.durationInFrames/job.fps;
  for(const w of job.words) {
    if(!w||typeof w.text!=='string'||!w.text.trim()||w.text.length>40) fail('Invalid caption word');
    if(!Number.isFinite(w.start)||!Number.isFinite(w.end)||w.start<0||w.start<lastEnd-0.001||w.end<=w.start||w.end>duration+0.001) fail('Words must be ordered, nonoverlapping and inside the clip (seconds)');
    lastEnd=w.end;
  }
  optional(job,'captionStyle',c=>{
    object(c,'captionStyle',['fontSizeRatio','position','maxWords','maxChars','color','activeColor','strokeColor','strokeWidth','shadow','entrance','keywords','keywordEaseDuration','strikeColor','strikeDuration','strikeWidth']);
    optional(c,'keywordEaseDuration',v=>number(v,'keywordEaseDuration',.001,.5)); optional(c,'strikeColor',color); optional(c,'strikeDuration',v=>number(v,'strikeDuration',.01,2));optional(c,'strikeWidth',v=>number(v,'strikeWidth',.5,30));
    optional(c,'fontSizeRatio',v=>number(v,'fontSizeRatio',.02,.2)); optional(c,'maxWords',v=>number(v,'maxWords',1,12,true)); optional(c,'maxChars',v=>number(v,'maxChars',1,100,true));
    for(const k of ['color','activeColor','strokeColor']) optional(c,k,color);
    optional(c,'strokeWidth',v=>number(v,'strokeWidth',0,8));
    optional(c,'shadow',s=>{object(s,'shadow',['color','blur','offsetX','offsetY']);optional(s,'color',color);optional(s,'blur',v=>number(v,'blur',0,30)); for(const k of ['offsetX','offsetY']) optional(s,k,v=>number(v,k,-30,30));});
    optional(c,'position',p=>{object(p,'position',['bottomRatio','sidesRatio']); optional(p,'bottomRatio',v=>number(v,'bottomRatio',0,.9));optional(p,'sidesRatio',v=>number(v,'sidesRatio',0,.4));});
    optional(c,'entrance',e=>{object(e,'entrance',['scale','translateY','duration']);optional(e,'scale',v=>number(v,'scale',.5,1.5)); optional(e,'translateY',v=>number(v,'translateY',-200,200)); optional(e,'duration',v=>number(v,'duration',.01,2));});
    optional(c,'keywords',kw=>{if(!kw||typeof kw!=='object'||Array.isArray(kw)||Object.keys(kw).length>100) fail('Invalid keywords');for(const [word,e] of Object.entries(kw)){if(!/^[\p{L}\p{N}'’-]{1,40}$/u.test(word)) fail('Invalid keyword');object(e,'keyword',['scale','color','offsetX','offsetY']);optional(e,'scale',v=>number(v,'scale',.5,2));optional(e,'color',color);for(const k of ['offsetX','offsetY']) optional(e,k,v=>number(v,k,-100,100));}});
  });
  optional(job,'headlineStyle',h=>{object(h,'headlineStyle',['topRatio','sidesRatio','fontSizeRatio','color','accentColor','strokeColor','strokeWidth']);for(const k of ['topRatio','sidesRatio']) optional(h,k,v=>number(v,k,0,k==='topRatio'?.9:.4));optional(h,'fontSizeRatio',v=>number(v,'fontSizeRatio',.02,.2));for(const k of ['color','accentColor','strokeColor']) optional(h,k,color);optional(h,'strokeWidth',v=>number(v,'strokeWidth',0,8));});
  for(const key of ['lowerThirds','overlays','transitions']) optional(job,key,entries=>{
    if(!Array.isArray(entries)||entries.length>100) fail(`Invalid ${key}`);
    for(const e of entries) {
      if(key==='transitions') {object(e,key,['time','rise','fall','color','opacity']); number(e.time,'time',0,duration); optional(e,'rise',v=>number(v,'rise',.01,2));optional(e,'fall',v=>number(v,'fall',.01,2));optional(e,'color',color);optional(e,'opacity',v=>number(v,'opacity',0,1));if(e.time-(e.rise??.1)<0||e.time+(e.fall??8/30)>duration) fail('Transition envelope outside clip');continue;}
      graphic(e,key,duration,key==='lowerThirds'?['name','title','entranceDuration']:['text','imagePath']);
      if(key==='lowerThirds') {text(e.name,'name',80);optional(e,'title',(v)=>text(v,'title',100));}
      else {if((e.text===undefined)===(e.imagePath===undefined)) fail('Overlay needs exactly one of text or imagePath');optional(e,'text',v=>text(v,'text',200));optional(e,'imagePath',image);}
    }
  });
  optional(job,'endcard',e=>{graphic(e,'endcard',duration,['text','subtitle','imagePath']);text(e.text,'endcard.text',120);optional(e,'subtitle',v=>text(v,'subtitle',200));optional(e,'imagePath',image);});
  optional(job,'background',b=>{object(b,'background',['color','fit','blur']);optional(b,'color',color);optional(b,'blur',v=>number(v,'blur',0,60));if(b.fit!==undefined&&!['contain','cover'].includes(b.fit)) fail('Invalid fit');});
  optional(job,'supportingVideo',s=>{object(s,'supportingVideo',['videoPath','layout','fit']);validateAssetPath(s.videoPath,['.mp4','.mov','.webm','.mkv']);if(!['side-by-side','stacked'].includes(s.layout)) fail('Invalid supporting layout');if(s.fit!==undefined&&!['contain','cover'].includes(s.fit)) fail('Invalid supporting fit');});
  optional(job,'renderOptions',r=>{object(r,'renderOptions',['crf','muted','audioBitrate','volume']);optional(r,'crf',v=>number(v,'crf',0,51,true));optional(r,'muted',v=>{if(typeof v!=='boolean') fail('muted must be boolean');});optional(r,'audioBitrate',v=>{if(typeof v!=='string'||! /^(64|96|128|160|192|256|320)k$/.test(v)) fail('Invalid audioBitrate');});optional(r,'volume',v=>number(v,'volume',0,2));});
  const inputs=[job.videoPath,job.fontPath,job.supportingVideo?.videoPath,...(job.overlays??[]).map(x=>x.imagePath),job.endcard?.imagePath].filter(Boolean);
  if(inputs.some(input=>sameAsset(job.outputPath,input))) fail('Output must not overwrite an input asset');
  return job;
}
