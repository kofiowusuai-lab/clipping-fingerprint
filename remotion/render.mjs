import {readFile,copyFile,mkdir,mkdtemp,rm,access} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {findBrowser} from './browser.mjs';
import {renderMedia,selectComposition} from '@remotion/renderer';
import {validateJob} from './schema.mjs';
const here=path.dirname(fileURLToPath(import.meta.url));
const file=process.argv[2]; if(!file) throw new Error('Usage: node render.mjs /absolute/job.json');
const job=validateJob(JSON.parse(await readFile(file,'utf8')));
for(const key of ['videoPath','fontPath']) await access(job[key]);
const chrome=await findBrowser();
await access(chrome); // No automatic browser download or paid/cloud renderer.
const temp=await mkdtemp(path.join(os.tmpdir(),'supoclip-remotion-'));
try {
  const publicDir=path.join(temp,'public');await mkdir(publicDir);
  await copyFile(job.videoPath,path.join(publicDir,'clip.mp4'));
  const font=`caption${path.extname(job.fontPath)}`;await copyFile(job.fontPath,path.join(publicDir,font));
  const inputProps={...job,media:'clip.mp4',font};
  // Stage only explicit, validated local assets; never expose an input directory.
  let assetIndex=0;
  const stage=async(source)=>{const name=`asset-${assetIndex++}${path.extname(source).toLowerCase()}`;await copyFile(source,path.join(publicDir,name));return name;};
  if(job.supportingVideo) inputProps.supportingVideo={...job.supportingVideo,media:await stage(job.supportingVideo.videoPath)};
  if(job.overlays) inputProps.overlays=await Promise.all(job.overlays.map(async(g)=>{const {imagePath,...rest}=g;return imagePath?{...rest,image:await stage(imagePath)}:rest;}));
  if(job.endcard) {const {imagePath,...rest}=job.endcard;inputProps.endcard=imagePath?{...rest,image:await stage(imagePath)}:rest;}
  delete inputProps.videoPath;delete inputProps.outputPath;delete inputProps.fontPath;
  const serveUrl=await bundle({enableCaching:false,entryPoint:path.join(here,'src/index.tsx'),publicDir,outDir:path.join(temp,'bundle')});
  const composition=await selectComposition({serveUrl,id:'CaptionedClip',inputProps,browserExecutable:chrome});
  await mkdir(path.dirname(path.resolve(job.outputPath)),{recursive:true});
  let last=-1;
  await renderMedia({serveUrl,composition,inputProps,outputLocation:path.resolve(job.outputPath),codec:'h264',audioCodec:'aac',audioBitrate:job.renderOptions?.audioBitrate??'128k',muted:job.renderOptions?.muted??false,pixelFormat:'yuv420p',crf:job.renderOptions?.crf??21,timeoutInMilliseconds:120000,offthreadVideoThreads:1,offthreadVideoCacheSizeInBytes:268435456,concurrency:1,browserExecutable:chrome,disableSharedMemoryCapture:true,disallowParallelEncoding:true,imageFormat:'png',frameRange:job.frameRange,overwrite:true,onProgress:({progress})=>{const n=Math.floor(progress*10);if(n!==last){console.log(`Render ${n*10}%`);last=n;}}});
  console.log(JSON.stringify({output:path.resolve(job.outputPath),frames:job.frameRange?job.frameRange[1]-job.frameRange[0]+1:composition.durationInFrames,width:composition.width,height:composition.height,fps:composition.fps}));
} finally {await rm(temp,{recursive:true,force:true});}
