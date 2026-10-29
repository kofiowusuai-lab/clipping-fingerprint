import {readFile,copyFile,mkdir,mkdtemp,rm,access,writeFile} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {findBrowser} from './browser.mjs';
import {renderStill,selectComposition,openBrowser} from '@remotion/renderer';
import {validateCreatorJob,validateCreatorPaths} from './creator-schema.mjs';
const here=path.dirname(fileURLToPath(import.meta.url));
const normalize=s=>s.toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');

/** Static glyph capture only. Python generates the animated band after this step. */
export async function renderCreatorAtlas(file) {
  if(!file || !path.isAbsolute(file))throw new Error('Usage: node remotion/render-creator-atlas.mjs /absolute/job.json');
  const raw=JSON.parse(await readFile(file,'utf8'));
  const allowed=['outputDir','fontPath','width','height','fps','durationInFrames','words','headline','keywords','captionY'];
  for(const key of Object.keys(raw))if(!allowed.includes(key))throw new Error(`Unknown job field: ${key}`);
  if(raw.headline!==undefined && typeof raw.headline!=='string')throw new Error('headline must be text');
  const job=validateCreatorPaths(validateCreatorJob({outputDir:raw.outputDir,fontPath:raw.fontPath,width:raw.width,height:raw.height,fps:raw.fps,durationInFrames:raw.durationInFrames,words:raw.words,headline:raw.headline?{text:raw.headline,start:0,end:raw.durationInFrames/(raw.fps??30),x:.5,y:.15,fontSizeRatio:.074}:undefined,caption:{position:raw.captionY??.80,maxWords:1},emphasis:{keywords:raw.keywords??[]}}),file);
  const chrome=await findBrowser();
  await access(chrome);
  const temp=await mkdtemp(path.join(os.tmpdir(),'creator-atlas-'));
  let browser;
  try {
    const publicDir=path.join(temp,'public');await mkdir(publicDir);
    await copyFile(job.fontPath,path.join(publicDir,'creator.ttf'));
    const serveUrl=await bundle({enableCaching:false,entryPoint:path.join(here,'src/creator-atlas.tsx'),publicDir,outDir:path.join(temp,'bundle')});
    browser=await openBrowser('chrome',{browserExecutable:chrome});
    await mkdir(job.outputDir,{recursive:false});
    const cellHeight=Math.ceil(200*job.width/1080);
    const keywords=new Set(job.emphasis.keywords.map(normalize));
    const sprites=[];const indices=new Map();
    const words=job.words.map(w=>{
      const color=w.emphasis||keywords.has(normalize(w.text))?'#d8ff36':'#ffffff';
      const key=JSON.stringify([w.text,color]);
      if(!indices.has(key)){indices.set(key,sprites.length);sprites.push({text:w.text,color});}
      return {...w,sprite:indices.get(key)};
    });
    const pages=[];const spriteManifest=[];
    const capture=async(props,output)=>{
      const inputProps={width:job.width,height:job.height,cellHeight,font:'creator.ttf',headline:job.headline?.text??'',...props};
      const composition=await selectComposition({serveUrl,id:'CreatorAtlas',inputProps,puppeteerInstance:browser,browserExecutable:chrome});
      await renderStill({serveUrl,composition,inputProps,output,imageFormat:'png',frame:0,puppeteerInstance:browser,browserExecutable:chrome,chromiumOptions:{disableWebSecurity:false},disableSharedMemoryCapture:true,timeoutInMilliseconds:120000});
    };
    for(let start=0;start<sprites.length;start+=10){
      const page=path.join(job.outputDir,`atlas-${String(pages.length).padStart(4,'0')}.png`);
      const batch=sprites.slice(start,start+10);
      await capture({mode:'atlas',sprites:batch},page);pages.push(page);
      batch.forEach((s,i)=>spriteManifest.push({...s,page,x:0,y:i*cellHeight,width:job.width,height:cellHeight}));
    }
    const heroPath=path.join(job.outputDir,'hero.png');
    await capture({mode:'hero',sprites:[]},heroPath);
    const manifest={version:1,kind:'creator-static-atlas',width:job.width,height:job.height,fps:job.fps,durationInFrames:job.durationInFrames,captionY:job.caption.position,cellHeight,words,sprites:spriteManifest,pages,heroPath,browserCaptures:pages.length+1};
    await writeFile(path.join(job.outputDir,'atlas-manifest.json'),JSON.stringify(manifest,null,2)+'\n',{flag:'wx'});
    return manifest;
  } finally {if(browser)await browser.close({silent:true});await rm(temp,{recursive:true,force:true});}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))renderCreatorAtlas(process.argv[2]).then(m=>console.log(JSON.stringify(m))).catch(e=>{console.error(e.stack??e);process.exitCode=1;});
