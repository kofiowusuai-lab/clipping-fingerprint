import React, {useEffect, useMemo, useState} from 'react';
import {AbsoluteFill, Composition, registerRoot, staticFile, useCurrentFrame, useVideoConfig, delayRender, continueRender, cancelRender} from 'remotion';
import {loadFont} from '@remotion/fonts';
import {smoothstep} from './animation';

type Timed = {start:number;end:number};
type Word = Timed & {text:string;emphasis:boolean};
type Note = Timed & {text:string;x:number;y:number;color:string;fontSizeRatio:number};
type Callout = Timed & {type:'arrow'|'circle';x:number;y:number;toX?:number;toY?:number;radius?:number;color:string;strokeRatio:number};
type Props = {
  font:string;width:number;height:number;fps:number;durationInFrames:number;
  words:Word[];preset:'clean-energy'|'aggressive';intensity:number;strokeRatio:number;
  caption:{position:number;maxWords:number;fontSizeRatio:number;color:string;highlight:string};
  emphasis:{keywords:string[];pop:number;translateYRatio:number;duration:number;easing:'smoothstep'|'cubic-out'};
  headline?:Note;labels:Note[];callouts:Callout[];
  counter?:Timed & {from:number;to:number;label:string;x:number;y:number;color:string};
  progress?:Timed & {x:number;y:number;width:number;height:number;color:string};
};
const defaults:Props = {font:'',width:1080,height:1920,fps:30,durationInFrames:30,words:[],preset:'clean-energy',intensity:.55,strokeRatio:.006,caption:{position:.72,maxWords:1,fontSizeRatio:.078,color:'#ffffff',highlight:'#d8ff36'},emphasis:{keywords:[],pop:.12,translateYRatio:.008,duration:.16,easing:'smoothstep'},labels:[],callouts:[]};
const normalize = (text:string) => text.toLocaleLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
// Grouping depends on the complete edited word list, never on the currently rendered frame.
const groupWords = (words:Word[],maxWords:number) => {
  const groups:Word[][]=[];let group:Word[]=[];
  for(const word of words) {
    if(group.length && (group.length>=maxWords || word.start-group[group.length-1].end>.35 || [...group,word].map(w=>w.text).join(' ').length>24)) {groups.push(group);group=[];}
    group.push(word);
    if(/[.!?]$/.test(word.text)){groups.push(group);group=[];}
  }
  if(group.length) groups.push(group);
  return groups;
};

export const CreatorGraphics:React.FC<Props> = (p) => {
  const frame=useCurrentFrame();const {width,height,fps}=useVideoConfig();const time=frame/fps;
  const [handle]=useState(()=>delayRender('Loading creator local font'));
  useEffect(()=>{if(!p.font){continueRender(handle);return;}loadFont({family:'CreatorLocal',url:staticFile(p.font),weight:'800'}).then(()=>continueRender(handle)).catch(cancelRender);},[p.font,handle]);
  const groups=useMemo(()=>groupWords(p.words,p.caption.maxWords),[p.words,p.caption.maxWords]);
  const group=groups.find(g=>time>=g[0].start && time<g[g.length-1].end);
  const keywords=useMemo(()=>new Set(p.emphasis.keywords.map(normalize)),[p.emphasis.keywords]);
  const active=(v:Timed)=>time>=v.start&&time<v.end;
  const progress=(v:Timed)=>Math.max(0,Math.min(1,(time-v.start)/(v.end-v.start)));
  const ease=(v:number)=>p.emphasis.easing==='cubic-out'?1-Math.pow(1-Math.max(0,Math.min(1,v)),3):smoothstep(v);
  const outline:React.CSSProperties={WebkitTextStroke:`${width*p.strokeRatio}px #101014`,paintOrder:'stroke fill',textShadow:`0 ${width*.004}px ${width*.01}px #000000a0`,fontWeight:800,lineHeight:1.12};
  const note=(v:Note,key:string)=>{
    // Keep labels within the mobile-safe region, including long words.
    const boxWidth=width*Math.min(.86,2*Math.min(v.x-.04,.96-v.x));
    const size=Math.min(width*v.fontSizeRatio,boxWidth/Math.max(3,Math.min(16,Math.max(...v.text.split(/\s/).map(s=>s.length))))/0.72);
    const intro=ease((time-v.start)/Math.min(.18,(v.end-v.start)/2));
    return <div key={key} style={{...outline,position:'absolute',left:v.x*width,top:v.y*height,transform:`translate(-50%, -50%) translateY(${(1-intro)*width*.012*p.intensity}px)`,width:boxWidth,maxHeight:height*.25,overflow:'hidden',overflowWrap:'anywhere',textAlign:'center',fontSize:size,color:v.color,opacity:intro}}>{v.text}</div>;
  };
  const counter=p.counter,bar=p.progress;
  return <AbsoluteFill style={{backgroundColor:'transparent',fontFamily:'CreatorLocal, sans-serif',overflow:'hidden'}}>
    {p.headline&&active(p.headline)?note(p.headline,'headline'):null}
    {p.labels.filter(active).map((v,i)=>note(v,`label-${i}`))}
    {group?<div style={{...outline,position:'absolute',left:'7%',width:'86%',top:p.caption.position*height,transform:'translateY(-50%)',textAlign:'center',fontSize:Math.min(width*p.caption.fontSizeRatio,width*.80/Math.max(1,...group.map(w=>w.text.length))/0.78),color:p.caption.color,lineHeight:1.25}}>{group.map((w,i)=>{
      const target=w.emphasis||keywords.has(normalize(w.text));
      const speaking=active(w);
      // Reveal each word on its spoken onset. Reserve the full phrase layout to avoid reflow.
      const revealed=time>=w.start;
      const intro=Math.max(0,Math.min(1,(time-w.start)/Math.min(.16,p.emphasis.duration)));
      const rise=ease(intro);
      const scale=.82+.18*rise+Math.sin(Math.PI*intro)*p.emphasis.pop*p.intensity;
      const reserve=width*p.caption.fontSizeRatio*w.text.length*.72*p.emphasis.pop*p.intensity/2;
      return <React.Fragment key={`${w.start}-${i}`}><span style={{display:'inline-block',whiteSpace:'nowrap',paddingLeft:reserve,paddingRight:reserve}}><span style={{display:'inline-block',opacity:revealed?1:0,color:target&&speaking?p.caption.highlight:p.caption.color,transform:`translateY(${height*p.emphasis.translateYRatio*(1-rise)*p.intensity}px) scale(${scale})`}}>{w.text}</span></span>{i<group.length-1?' ':''}</React.Fragment>;
    })}</div>:null}
    {p.callouts.filter(active).map((v,i)=>{
      const opacity=ease((time-v.start)/Math.min(.12,(v.end-v.start)/2));
      const x=v.x*width,y=v.y*height,x2=(v.toX??v.x)*width,y2=(v.toY??v.y)*height;
      const angle=Math.atan2(y2-y,x2-x),head=width*.035;
      return <svg key={`callout-${i}`} width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{position:'absolute',inset:0,opacity,overflow:'visible'}}><g fill="none" stroke={v.color} strokeWidth={width*v.strokeRatio} strokeLinecap="round" strokeLinejoin="round">
        {v.type==='circle'?<circle cx={x} cy={y} r={(v.radius??.1)*width}/>:<><line x1={x} y1={y} x2={x2} y2={y2}/><path d={`M ${x2-head*Math.cos(angle-.5)} ${y2-head*Math.sin(angle-.5)} L ${x2} ${y2} L ${x2-head*Math.cos(angle+.5)} ${y2-head*Math.sin(angle+.5)}`}/></>}
      </g></svg>;
    })}
    {counter&&active(counter)?note({...counter,text:`${counter.label}${counter.label?' ':''}${Math.round(counter.from+(counter.to-counter.from)*progress(counter))}`,fontSizeRatio:.075},'counter'):null}
    {bar&&active(bar)?<div style={{position:'absolute',left:(bar.x-bar.width/2)*width,top:bar.y*height,width:bar.width*width,height:bar.height*height,borderRadius:height*bar.height,backgroundColor:'#10101480',overflow:'hidden'}}><div style={{height:'100%',width:`${100*progress(bar)}%`,backgroundColor:bar.color}}/></div>:null}
  </AbsoluteFill>;
};
const Root=()=> <Composition id="CreatorGraphics" component={CreatorGraphics} width={1080} height={1920} fps={30} durationInFrames={30} defaultProps={defaults} calculateMetadata={({props})=>({width:props.width,height:props.height,fps:props.fps,durationInFrames:props.durationInFrames})}/>;
registerRoot(Root);
