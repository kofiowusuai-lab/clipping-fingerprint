import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
export const styles = JSON.parse(fs.readFileSync(fileURLToPath(new URL('../configs/creator/styles.json', import.meta.url)), 'utf8'));
const fail = (s) => {throw new Error(s);};
const object = (v, name, keys) => {
  if (!v || typeof v !== 'object' || Array.isArray(v)) fail(`${name} must be an object`);
  for (const k of Object.keys(v)) if (!keys.includes(k)) fail(`${name}: unknown field ${k}`);
  return v;
};
const num = (v, name, min, max, integer = false) => {
  if (typeof v !== 'number' || !Number.isFinite(v) || v < min || v > max || (integer && !Number.isInteger(v))) fail(`${name} must be ${integer?'integer ':''}${min}..${max}`);
  return v;
};
const text = (v, name, max = 140) => {
  if (typeof v !== 'string' || !v.trim() || v.length > max || /[\x00-\x1f\x7f]/.test(v)) fail(`${name} must be nonempty text <=${max} characters`);
  return v.trim();
};
const color = (v, name) => /^#[0-9a-f]{6}$/i.test(v ?? '') ? v : fail(`${name} must be #RRGGBB`);
const absolute = (v, name) => typeof v === 'string' && path.isAbsolute(v) && !v.includes('\0') ? path.resolve(v) : fail(`${name} must be an absolute local path`);
const list = (v, name, max = 1000) => Array.isArray(v) && v.length <= max ? v : fail(`${name} must be an array <=${max}`);
const bool = (v, name) => typeof v === 'boolean' ? v : fail(`${name} must be boolean`);
const choose = (v, choices, name) => choices.includes(v) ? v : fail(`${name} must be ${choices.join('|')}`);

/** All event/word times are seconds on the EDITED timeline. Coordinates are normalized. */
export function validateCreatorJob(raw) {
  object(raw, 'job', ['outputDir','fontPath','width','height','fps','durationInFrames','words','preset','caption','headline','labels','callouts','counter','progress','intensity','emphasis']);
  const preset = choose(raw.preset ?? 'clean-energy', Object.keys(styles), 'preset');
  const style = styles[preset];
  const width = num(raw.width ?? 1080, 'width', 240, 2160, true);
  const height = num(raw.height ?? 1920, 'height', 240, 3840, true);
  const fps = choose(raw.fps ?? 30, [24,30], 'fps');
  const durationInFrames = num(raw.durationInFrames, 'durationInFrames', 1, 18000, true);
  const duration = durationInFrames / fps;
  const timed = (v, name) => {
    const start = num(v.start, `${name}.start (seconds)`, 0, duration);
    const end = num(v.end, `${name}.end (seconds)`, 0, duration);
    if (end <= start) fail(`${name}.end must exceed start`);
    return {start,end};
  };
  const xy = (v, name, defaults = {x:0.5,y:0.22}) => ({x:num(v.x ?? defaults.x,`${name}.x`,0.06,0.94), y:num(v.y ?? defaults.y,`${name}.y`,0.08,0.88)});
  const words = list(raw.words ?? [], 'words', 20000).map((w,i) => {
    object(w,`words[${i}]`,['text','start','end','emphasis']);
    const value = text(w.text,'word.text',40);
    if (/\s/.test(value)) fail('Each word must be one token, not a phrase');
    return {text:value,...timed(w,`word[${i}]`),emphasis:bool(w.emphasis ?? false,'word.emphasis')};
  });
  words.forEach((w,i) => {if (i && w.start < words[i-1].end - 1e-8) fail('words must be ordered and non-overlapping');});
  const c = object(raw.caption ?? {}, 'caption', ['position','maxWords','fontSizeRatio','color','highlight']);
  let position = c.position ?? style.caption.position;
  if (typeof position === 'string') position = ({top:0.22,middle:0.50,bottom:0.72})[choose(position,['top','middle','bottom'],'caption.position')];
  const caption = {position:num(position,'caption.position',0.15,0.82),maxWords:num(c.maxWords ?? style.caption.maxWords,'caption.maxWords',1,6,true),fontSizeRatio:num(c.fontSizeRatio ?? style.caption.fontSizeRatio,'caption.fontSizeRatio',0.045,0.11),color:color(c.color ?? style.caption.color,'caption.color'),highlight:color(c.highlight ?? style.caption.highlight,'caption.highlight')};
  const e = object(raw.emphasis ?? {},'emphasis',['keywords','pop','translateYRatio','duration','easing']);
  const emphasis = {keywords:list(e.keywords ?? [],'emphasis.keywords',200).map(k=>text(k,'keyword',40).toLocaleLowerCase()),pop:num(e.pop ?? style.emphasis.pop,'emphasis.pop',0,0.4),translateYRatio:num(e.translateYRatio ?? style.emphasis.translateYRatio,'emphasis.translateYRatio',0,0.03),duration:num(e.duration ?? style.emphasis.duration,'emphasis.duration (seconds)',0.03,0.5),easing:choose(e.easing ?? style.emphasis.easing,['smoothstep','cubic-out'],'emphasis.easing')};
  const annotation = (v,name,isHeadline=false) => {
    object(v,name,['text','start','end','x','y','color','fontSizeRatio']);
    return {text:text(v.text,`${name}.text`,isHeadline?100:70),...timed(v,name),...xy(v,name),color:color(v.color ?? caption.color,`${name}.color`),fontSizeRatio:num(v.fontSizeRatio ?? (isHeadline?style.headlineSizeRatio:0.052),`${name}.fontSizeRatio`,0.03,0.1)};
  };
  const labels = list(raw.labels ?? [],'labels',100).map((v,i)=>annotation(v,`labels[${i}]`));
  const callouts = list(raw.callouts ?? [],'callouts',100).map((v,i)=>{
    const name=`callouts[${i}]`;
    object(v,name,['type','start','end','x','y','toX','toY','radius','color','strokeRatio']);
    const type=choose(v.type,['arrow','circle'],`${name}.type`);
    if (type === 'arrow' && v.radius !== undefined) fail('arrow cannot have radius');
    if (type === 'circle' && (v.toX !== undefined || v.toY !== undefined)) fail('circle cannot have arrow endpoints');
    const base={type,...timed(v,name),...xy(v,name),color:color(v.color ?? caption.highlight,`${name}.color`),strokeRatio:num(v.strokeRatio ?? 0.009,`${name}.strokeRatio`,0.003,0.025)};
    if(type==='arrow') {
      const toX=num(v.toX,`${name}.toX`,0.06,0.94),toY=num(v.toY,`${name}.toY`,0.08,0.88);
      if(Math.hypot(toX-base.x,toY-base.y)<0.03) fail('arrow endpoints too close');
      return {...base,toX,toY};
    }
    const radius=num(v.radius ?? 0.10,`${name}.radius (fraction of width)`,0.025,0.3);
    if(base.x-radius<0.02 || base.x+radius>0.98 || base.y-radius*width/height<0.03 || base.y+radius*width/height>0.95) fail('circle outside safe bounds');
    return {...base,radius};
  });
  let counter,progress;
  if(raw.counter !== undefined) {
    const v=object(raw.counter,'counter',['start','end','from','to','label','x','y','color']);
    counter={...timed(v,'counter'),...xy(v,'counter',{x:0.5,y:0.34}),from:num(v.from ?? 0,'counter.from',-9999,9999,true),to:num(v.to,'counter.to',-9999,9999,true),label:v.label === undefined?'':text(v.label,'counter.label',24),color:color(v.color ?? caption.highlight,'counter.color')};
  }
  if(raw.progress !== undefined) {
    const v=object(raw.progress,'progress',['start','end','x','y','width','height','color']);
    progress={...timed(v,'progress'),...xy(v,'progress',{x:0.5,y:0.86}),width:num(v.width ?? 0.7,'progress.width',0.1,0.85),height:num(v.height ?? 0.006,'progress.height',0.002,0.025),color:color(v.color ?? caption.highlight,'progress.color')};
    if(progress.x-progress.width/2<0.04 || progress.x+progress.width/2>0.96) fail('progress outside safe bounds');
  }
  return {outputDir:absolute(raw.outputDir,'outputDir'),fontPath:absolute(raw.fontPath,'fontPath'),width,height,fps,durationInFrames,words,preset,caption,emphasis,intensity:num(raw.intensity ?? style.intensity,'intensity',0,1),headline:raw.headline !== undefined?annotation(raw.headline,'headline',true):undefined,labels,callouts,counter,progress,strokeRatio:style.strokeRatio};
}

/** Refuse existing output, symlink aliases, input ancestors, and collisions. No output cleanup. */
export function validateCreatorPaths(job, jobFile) {
  const font = fs.realpathSync(job.fontPath);
  if (!fs.statSync(font).isFile() || path.extname(font).toLowerCase() !== '.ttf') fail('fontPath must be an existing local .ttf file');
  const header=Buffer.alloc(4);const fd=fs.openSync(font,'r');try {fs.readSync(fd,header,0,4,0);}finally{fs.closeSync(fd);}
  if (!header.equals(Buffer.from([0,1,0,0])) && header.toString() !== 'true') fail('fontPath does not have a TrueType header');
  if (fs.existsSync(job.outputDir) || (()=>{try{fs.lstatSync(job.outputDir);return true;}catch(e){if(e.code==='ENOENT')return false;throw e;}})()) fail('outputDir must be a fresh, nonexistent directory');
  const parent=fs.realpathSync(path.dirname(job.outputDir));
  const out=path.join(parent,path.basename(job.outputDir));
  for (const input of [font,...(jobFile?[fs.realpathSync(jobFile)]:[])]) {
    if(input===out || input.startsWith(out+path.sep)) fail('outputDir collides with an input');
  }
  return {...job,fontPath:font,outputDir:out};
}
