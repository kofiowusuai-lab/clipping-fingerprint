import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Composition, Img, OffthreadVideo, registerRoot, staticFile, useCurrentFrame, useVideoConfig, delayRender, continueRender, cancelRender, interpolate} from 'remotion';
import {loadFont} from '@remotion/fonts';
import {wordEnvelope, entranceEnvelope} from './animation';

type Word = {text: string; start: number; end: number};
type Color = string;
type Graphic = {start:number; end:number; entranceDuration?:number; xRatio?:number; yRatio?:number; widthRatio?:number; fontSizeRatio?:number; color?:Color; backgroundColor?:Color; name?:string; title?:string; text?:string; subtitle?:string; image?:string};
type CaptionStyle = {strikeColor?:Color;strikeDuration?:number;strikeWidth?:number;keywordEaseDuration?:number;fontSizeRatio?:number; position?:{bottomRatio?:number;sidesRatio?:number};maxWords?:number;maxChars?:number;color?:Color;activeColor?:Color;strokeColor?:Color;strokeWidth?:number;shadow?:{color?:Color;blur?:number;offsetX?:number;offsetY?:number};entrance?:{scale?:number;translateY?:number;duration?:number};keywords?:Record<string,{scale?:number;color?:Color;offsetX?:number;offsetY?:number}>};
type Props = {media: string; font: string; words: Word[]; style: 'clean' | 'bold'; headline: string; headlineAccent: string; headlineDuration: number; strikeWords: string[]; durationInFrames: number; fps: number; width: number; height: number;captionStyle?:CaptionStyle;headlineStyle?:{topRatio?:number;sidesRatio?:number;fontSizeRatio?:number;color?:Color;accentColor?:Color;strokeColor?:Color;strokeWidth?:number};lowerThirds?:Graphic[];overlays?:Graphic[];endcard?:Graphic;background?:{color?:Color;fit?:'contain'|'cover';blur?:number};supportingVideo?:{media:string;layout:'side-by-side'|'stacked';fit?:'contain'|'cover'};transitions?:{time:number;rise?:number;fall?:number;color?:Color;opacity?:number}[];renderOptions?:{volume?:number;muted?:boolean}};
const defaults: Props = {media: '', font: '', words: [], style: 'clean', headline: '', headlineAccent: '#ffffff', headlineDuration: 3, strikeWords: [], durationInFrames: 90, fps: 30, width: 720, height: 1280};
const groupWords = (words: Word[], maxWords=3,maxChars=21) => {
  const groups: Word[][] = []; let group: Word[] = [];
  for (const word of words) {
    if (group.length && (group.length >= maxWords || [...group,word].map(w=>w.text).join(' ').length > maxChars || word.start-group[group.length-1].end > 0.4)) {groups.push(group); group=[];}
    group.push(word); if (/[.!?]$/.test(word.text)) {groups.push(group); group=[];}
  }
  if (group.length) groups.push(group); return groups;
};
const normalize=(text:string)=>text.toLocaleLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
const Clip: React.FC<Props> = (props) => {
  const frame=useCurrentFrame(); const {fps,width,height}=useVideoConfig(); const time=frame/fps;
  const [fontHandle]=useState(()=>delayRender('Loading local caption font'));
  useEffect(()=>{if (!props.font) {continueRender(fontHandle); return;} loadFont({family:'ClipCaption',url:staticFile(props.font),weight:'800'}).then(()=>continueRender(fontHandle)).catch(cancelRender);},[props.font,fontHandle]);
  const c=props.captionStyle??{}, h=props.headlineStyle??{}, bg=props.background??{};
  const group=groupWords(props.words,c.maxWords,c.maxChars).find(g=>time>=g[0].start && time<g[g.length-1].end);
  const bold=props.style==='bold'; const entrance=c.entrance;
  const progress=group?interpolate(time-group[0].start,[0,entrance?.duration??4/fps],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'}):1;
  const initialScale=entrance?.scale??(bold?.97:1), scale=initialScale+(1-initialScale)*progress;
  const headlineOpacity=interpolate(frame,[0,5],[0,1],{extrapolateRight:'clamp'});
  const strikeTargets=new Set((props.strikeWords??[]).map(normalize));
  const keywords=new Map(Object.entries(c.keywords??{}).map(([k,v])=>[normalize(k),v]));
  const shadow=c.shadow?`${c.shadow.offsetX??0}px ${c.shadow.offsetY??2}px ${c.shadow.blur??5}px ${c.shadow.color??'#000000'}`:'0 2px 5px black, 1px 0 2px black, -1px 0 2px black';
  const active=(g:Graphic)=>time>=g.start&&time<g.end;
  const graphicStyle=(g:Graphic):React.CSSProperties=>({position:'absolute',left:width*(g.xRatio??.065),top:height*(g.yRatio??.84),width:width*(g.widthRatio??.87),fontSize:width*(g.fontSizeRatio??.045),color:g.color??'#ffffff',backgroundColor:g.backgroundColor??'#101014',padding:width*.02,boxSizing:'border-box',fontWeight:800,lineHeight:1.2,overflowWrap:'anywhere'});
  const video=(media:string,fit:'contain'|'cover',muted:boolean)=> <OffthreadVideo src={staticFile(media)} muted={muted} volume={props.renderOptions?.volume??1} style={{width:'100%',height:'100%',objectFit:fit}}/>;
  return <AbsoluteFill style={{backgroundColor:bg.color??'#101014',color:'white',fontFamily:'ClipCaption, sans-serif'}}>
    {props.media?<AbsoluteFill>
      {bg.blur?<AbsoluteFill style={{filter:`blur(${bg.blur}px)`,transform:'scale(1.08)'}}><OffthreadVideo src={staticFile(props.media)} muted style={{width:'100%',height:'100%',objectFit:'cover'}}/></AbsoluteFill>:null}
      <AbsoluteFill style={{display:'flex',flexDirection:props.supportingVideo?.layout==='stacked'?'column':'row'}}>
        <div style={{position:'relative',flex:1,minWidth:0,minHeight:0}}>{video(props.media,bg.fit??'contain',props.renderOptions?.muted??false)}</div>
        {props.supportingVideo?<div style={{position:'relative',flex:1,minWidth:0,minHeight:0}}>{video(props.supportingVideo.media,props.supportingVideo.fit??'cover',true)}</div>:null}
      </AbsoluteFill>
    </AbsoluteFill>:null}
    {props.headline && time<props.headlineDuration?<div style={{position:'absolute',top:height*(h.topRatio??.075),left:width*(h.sidesRatio??.07),right:width*(h.sidesRatio??.07),textAlign:'center',fontSize:width*(h.fontSizeRatio??.075),fontWeight:800,lineHeight:1.12,textShadow:'0 3px 8px black',WebkitTextStroke:`${h.strokeWidth??0}px ${h.strokeColor??'#000000'}`,paintOrder:'stroke fill',opacity:headlineOpacity}}>{props.headline.split('\n').map((line,i,lines)=><div key={i} style={{color:i===lines.length-1?(h.accentColor??props.headlineAccent):(h.color??'white')}}>{line}</div>)}</div>:null}
    {group?<div style={{position:'absolute',bottom:height*(c.position?.bottomRatio??.19),left:width*(c.position?.sidesRatio??.065),right:width*(c.position?.sidesRatio??.065),textAlign:'center',fontSize:width*(c.fontSizeRatio??(bold?.095:.078)),fontWeight:800,lineHeight:1.15,textShadow:shadow,WebkitTextStroke:`${c.strokeWidth??0}px ${c.strokeColor??'#000000'}`,paintOrder:'stroke fill',transform:`translateY(${(entrance?.translateY??0)*(1-progress)}px) scale(${scale})`}}>{group.map((w,i)=>{
      const target=strikeTargets.has(normalize(w.text)), struck=target&&time>=w.start, speaking=time>=w.start&&time<w.end;
      const kw=keywords.get(normalize(w.text));
      const emphasis=wordEnvelope(time,w.start,w.end,c.keywordEaseDuration??.08);
      const strikeColor=c.strikeColor??'#ff4148';
      const strikeProgress=interpolate(time,[w.start,w.start+(c.strikeDuration??.22)],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
      return <React.Fragment key={`${w.start}-${i}`}><span style={{position:target?'relative':undefined,display:target||kw?'inline-block':undefined,color:struck?strikeColor:(speaking?kw?.color:undefined)??(speaking&&(bold||c.activeColor!==undefined)?(c.activeColor??'#ffe000'):(c.color??'white')),transform:kw?`translate(${(kw.offsetX??0)*emphasis}px,${(kw.offsetY??0)*emphasis}px) scale(${1+((kw.scale??1)-1)*emphasis})`:undefined}}>{bold?w.text.toUpperCase():w.text}{struck?<span style={{position:'absolute',height:c.strikeWidth??width/720*5,backgroundColor:strikeColor,left:0,right:0,top:'53%',borderRadius:3,boxShadow:'0 1px 3px black',transform:`scaleX(${strikeProgress})`,transformOrigin:'left center'}}/>:null}</span>{i<group.length-1?' ':''}</React.Fragment>;
    })}</div>:null}
    {(props.lowerThirds??[]).filter(active).map((g,i)=><div key={`lower-${i}`} style={{...graphicStyle(g),opacity:entranceEnvelope(time,g.start,g.end,g.entranceDuration??.15),transform:`translateY(${width*.015*(1-entranceEnvelope(time,g.start,g.end,g.entranceDuration??.15))}px)`}}><div>{g.name}</div>{g.title?<div style={{fontSize:'65%',opacity:.85}}>{g.title}</div>:null}</div>)}
    {(props.overlays??[]).filter(active).map((g,i)=><div key={`overlay-${i}`} style={graphicStyle(g)}>{g.image?<Img src={staticFile(g.image)} style={{display:'block',width:'100%',maxHeight:height*.5,objectFit:'contain'}}/>:g.text}</div>)}
    {props.endcard&&active(props.endcard)?<AbsoluteFill style={{backgroundColor:props.endcard.backgroundColor??'#101014'}}><div style={{...graphicStyle({...props.endcard,yRatio:props.endcard.yRatio??.35}),textAlign:'center'}}>{props.endcard.image?<Img src={staticFile(props.endcard.image)} style={{width:'40%',maxHeight:height*.3,objectFit:'contain'}}/>:null}<div>{props.endcard.text}</div>{props.endcard.subtitle?<div style={{fontSize:'65%',marginTop:width*.02}}>{props.endcard.subtitle}</div>:null}</div></AbsoluteFill>:null}
    {(props.transitions??[]).map((t,i)=>{const delta=time-t.time,rise=t.rise??.1,fall=t.fall??8/30; if(delta< -rise||delta>fall)return null;const v=delta<=0?1+delta/rise:1-delta/fall;const opacity=(v*v*(3-2*v))*(t.opacity??1);return <AbsoluteFill key={`luma-${i}`} style={{backgroundColor:t.color??'#ffffff',opacity}}/>;})}
  </AbsoluteFill>;
};
const Root = () => <Composition id="CaptionedClip" component={Clip} width={720} height={1280} fps={30} durationInFrames={90} defaultProps={defaults} calculateMetadata={({props})=>({durationInFrames:props.durationInFrames,fps:props.fps,width:props.width,height:props.height})}/>;
registerRoot(Root);
