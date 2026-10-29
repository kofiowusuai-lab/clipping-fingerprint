"""Measure picture timestamp mapping, not a lip-reading model."""
import json, subprocess
from pathlib import Path
import cv2
import numpy as np
# NumPy FFT correlation avoids adding a dependency for one alignment check.
def correlate_valid(a,b):
    n=1 << (len(a)+len(b)-2).bit_length()
    conv=np.fft.irfft(np.fft.rfft(a,n)*np.fft.rfft(b[::-1],n),n)
    return conv[len(b)-1:len(a)]
R=Path(__file__).resolve().parents[1]; O=R/'outputs/creator-engine/Vpd-xFMfCq0'
c=json.loads((O/'clip-plan.json').read_text()); old=Path(c['outputDir'])/'clean-energy/telegram.mp4'
src=cv2.VideoCapture(c['source']); dst=cv2.VideoCapture(str(old)); rows=[]
for t in [1,12,28,35,45,59]:
    frame=round(t*c['fps']); dst.set(cv2.CAP_PROP_POS_FRAMES,frame);ok,f=dst.read(); assert ok
    shot=next(s for s in c['shots'] if s['startFrame']<=frame<s['endFrame']);x,y,w,h=shot['crop'];fh=round(c['width']*h/w)//2*2;top=(c['height']-fh)//2
    target=cv2.resize(f[top:top+fh],(160,148)).astype(float)
    expected=c['start']+frame/c['fps']; candidates=[]
    for sf in range(round((expected-.65)*30),round((expected+.65)*30)+1):
        src.set(cv2.CAP_PROP_POS_FRAMES,sf);ok,s=src.read();assert ok
        sample=cv2.resize(s[y:y+h,x:x+w],(160,148)).astype(float)
        candidates.append((float(np.mean((target-sample)**2)),sf/30))
    err,matched=min(candidates)
    rows.append({'outputTime':frame/c['fps'],'expectedExcerptTime':expected,'matchedExcerptTime':matched,'pictureOffsetSeconds':matched-expected,'mse':err})
src.release();dst.release()
def audio(p,start,duration):
    return np.frombuffer(subprocess.run(['ffmpeg','-v','error','-ss',str(start),'-i',str(p),'-t',str(duration),'-vn','-ac','1','-ar','8000','-f','f32le','-'],capture_output=True,check=True).stdout,dtype='<f4')
# Compare actual excerpt audio to the unsectioned archive, with +/- 0.5s handles.
a=audio(c['source'],c['start'],10);ref=audio(R/'.local/uploads/youtube-cache/Vpd-xFMfCq0/scan.mp4',765+c['start']-.5,11)
cc=correlate_valid(ref,a);shift=int(np.argmax(cc));audio_offset=shift/8000-.5
# Compare a source excerpt video frame to full-archive frames in its own geometry.
e=cv2.VideoCapture(c['source']);full=cv2.VideoCapture(str(R/'.local/uploads/youtube-cache/Vpd-xFMfCq0/scan.mp4')); picture=[]
for t in [25,55,80]:
    e.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,f=e.read();assert ok;target=cv2.resize(f,(160,90)).astype(float); candidates=[]
    for sf in range(round((765+t-.5)*30),round((765+t+.5)*30)+1):
        full.set(cv2.CAP_PROP_POS_FRAMES,sf);ok,g=full.read();assert ok;g=cv2.resize(g,(160,90)).astype(float);candidates.append((float(np.mean((target-g)**2)),sf/30))
    err,matched=min(candidates);picture.append({'excerptTime':t,'archiveTime':matched,'offsetFromExpected':matched-(765+t),'mse':err})
e.release();full.release()
report={'oldExportPictureMapping':rows,'excerptAudioOffsetAgainstArchiveSeconds':audio_offset,'excerptPictureMappingAgainstArchive':picture,'limitations':'Pixel and waveform matching measures processing-induced offsets; it does not certify that the original stream has perfect speech-to-mouth synchrony.'}
(O/'sync-diagnosis.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
