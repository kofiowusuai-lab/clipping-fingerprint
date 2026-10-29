import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Composition, registerRoot, staticFile, delayRender, continueRender, cancelRender} from 'remotion';
import {loadFont} from '@remotion/fonts';

type Sprite = {text:string;color:string};
type Props = {width:number;height:number;cellHeight:number;font:string;mode:'atlas'|'hero';sprites:Sprite[];headline:string};
const defaults:Props={width:1080,height:1920,cellHeight:200,font:'creator.ttf',mode:'atlas',sprites:[],headline:''};
const Graphics:React.FC<Props>=(p)=>{
  const [handle]=useState(()=>delayRender('Local atlas font'));
  const [ready,setReady]=useState(false);
  useEffect(()=>{loadFont({family:'CreatorAtlas',url:staticFile(p.font),weight:'800'}).then(()=>{setReady(true);continueRender(handle);}).catch(cancelRender);},[p.font,handle]);
  const outline:React.CSSProperties={fontFamily:'CreatorAtlas',fontWeight:800,WebkitTextStroke:`${p.width*.006}px #101014`,paintOrder:'stroke fill',textShadow:`0 ${p.width*.004}px ${p.width*.01}px #000000a0`};
  const fittedSize=(text:string)=>{
    const base=Math.min(p.width*.078,p.width*.80/Math.max(1,text.length)/.78);
    if(!ready)return base;
    const canvas=document.createElement('canvas');const ctx=canvas.getContext('2d')!;
    ctx.font=`800 ${base}px CreatorAtlas`;
    return Math.min(base,base*(p.width*.86)/(ctx.measureText(text).width+p.width*.012));
  };
  const heroSize=Math.min(p.width*.074,p.width*.86/Math.max(3,Math.min(16,Math.max(...p.headline.split(/\s/).map(s=>s.length))))/.72);
  return <AbsoluteFill style={{backgroundColor:'transparent',overflow:'hidden'}}>
    {p.mode==='hero'?<div style={{...outline,position:'absolute',left:'7%',width:'86%',top:p.height*.15,transform:'translateY(-50%)',textAlign:'center',fontSize:heroSize,lineHeight:1.12,overflowWrap:'anywhere',color:'#ffffff'}}>{p.headline}</div>:p.sprites.map((s,i)=><div key={i} style={{position:'absolute',left:0,top:i*p.cellHeight,width:p.width,height:p.cellHeight,display:'flex',alignItems:'center',justifyContent:'center'}}><span style={{...outline,color:s.color,fontSize:fittedSize(s.text),lineHeight:1.25,whiteSpace:'nowrap'}}>{s.text}</span></div>)}
  </AbsoluteFill>;
};
const Root=()=> <Composition id="CreatorAtlas" component={Graphics} width={1080} height={2000} fps={30} durationInFrames={1} defaultProps={defaults} calculateMetadata={({props})=>({width:props.width,height:props.mode==='hero'?props.height:props.cellHeight*Math.max(1,props.sprites.length)})}/>;
registerRoot(Root);
