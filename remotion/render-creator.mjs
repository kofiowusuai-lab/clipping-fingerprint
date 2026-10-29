import {readFile,copyFile,mkdir,mkdtemp,rm,access,readdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {findBrowser} from './browser.mjs';
import {renderFrames,selectComposition} from '@remotion/renderer';
import {validateCreatorJob,validateCreatorPaths} from './creator-schema.mjs';
const here=path.dirname(fileURLToPath(import.meta.url));

export async function renderCreator(file) {
  if(!file || !path.isAbsolute(file)) throw new Error('Usage: node render-creator.mjs /absolute/job.json');
  const job=validateCreatorPaths(validateCreatorJob(JSON.parse(await readFile(file,'utf8'))),file);
  const chrome=await findBrowser();
  await access(chrome); // Never invoke ensureBrowser() or download assets.
  const temp=await mkdtemp(path.join(os.tmpdir(),'supoclip-creator-'));
  try {
    const publicDir=path.join(temp,'public');await mkdir(publicDir);
    await copyFile(job.fontPath,path.join(publicDir,'creator.ttf')); // Stage font only, never source media.
    const {outputDir,fontPath,...props}=job;
    const inputProps={...props,font:'creator.ttf'};
    const serveUrl=await bundle({enableCaching:false,entryPoint:path.join(here,'src/creator.tsx'),publicDir,outDir:path.join(temp,'bundle')});
    const composition=await selectComposition({serveUrl,id:'CreatorGraphics',inputProps,browserExecutable:chrome,timeoutInMilliseconds:120000});
    // Atomic exclusive claim: refuse even an empty preexisting folder, including races.
    await mkdir(outputDir,{recursive:false});
    const result=await renderFrames({serveUrl,composition,inputProps,outputDir,imageFormat:'png',imageSequencePattern:'frame-[frame].[ext]',concurrency:1,disableSharedMemoryCapture:true,timeoutInMilliseconds:120000,browserExecutable:chrome,onStart:()=>{},onFrameUpdate:()=>{}});
    const files=(await readdir(outputDir)).filter(f=>/^frame-\d+\.png$/.test(f)).sort();
    if(files.length!==job.durationInFrames) throw new Error(`Incomplete PNG sequence: ${files.length}/${job.durationInFrames}`);
    const pad=files[0].match(/^frame-(\d+)\.png$/)[1].length;
    for(let i=0;i<files.length;i++) if(files[i]!==`frame-${String(i).padStart(pad,'0')}.png`) throw new Error(`Unexpected PNG numbering at ${i}`);
    const manifest={version:1,kind:'creator-graphics-only',preset:job.preset,outputDir,width:job.width,height:job.height,fps:job.fps,durationInFrames:job.durationInFrames,durationSeconds:job.durationInFrames/job.fps,imageFormat:'png',alpha:true,startNumber:0,frameCount:files.length,firstFile:files[0],lastFile:files.at(-1),imageSequenceName:result.assetsInfo.imageSequenceName,ffmpegPattern:path.join(outputDir,`frame-%0${pad}d.png`),files,settings:JSON.parse(JSON.stringify(props)),notes:['All times are edited-timeline seconds; all coordinates normalized.','Graphics are editorial opt-ins, not automatic semantic recognition.','No video decoding, picture layout, media punch-ins, audio, branding or endcard. FFmpeg owns picture and final overlay encode.']};
    await writeFile(path.join(outputDir,'manifest.json'),JSON.stringify(manifest,null,2)+'\n',{flag:'wx'});
    return manifest;
  } finally {await rm(temp,{recursive:true,force:true});} // Only our mkdtemp; never delete arbitrary output.
}
if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  renderCreator(process.argv[2]).then(m=>console.log(JSON.stringify(m))).catch(e=>{console.error(e.stack??e);process.exitCode=1;});
}
