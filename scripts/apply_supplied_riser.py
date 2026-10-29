"""Use K's supplied riser, unchanged in pitch/speed; remove rejected FX."""
import json
import subprocess
import wave
from pathlib import Path
import imageio_ffmpeg
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'outputs/serhant-v3'
OUT=ROOT/'outputs/serhant-v5'; OUT.mkdir(exist_ok=True)
FF=imageio_ffmpeg.get_ffmpeg_exe()
SOURCE=ROOT/'.local/uploads/youtube-cache/K213Pn9ffIc/full.mp4'
report=json.loads((BASE/'verification.json').read_text())

def run(args):
    p=subprocess.run(args,capture_output=True)
    if p.returncode: raise RuntimeError(p.stderr.decode()[-4000:])
    return p

speech=[]
for a,b,_ in report['source_beats']:
    raw=run([FF,'-v','error','-ss',str(a),'-i',str(SOURCE),'-t',str(b-a),'-vn','-ar','48000','-ac','2','-f','f32le','pipe:1']).stdout
    x=np.frombuffer(raw,dtype='<f4').reshape(-1,2).copy()
    n=round((b-a)*30)*1600
    speech.append(np.pad(x,((0,max(0,n-len(x))),(0,0)))[:n])
speech=np.concatenate(speech)
asset=ROOT/'outputs/assets/KiJX7agcIns.wav'
with wave.open(str(asset),'rb') as w:
    assert w.getframerate()==48000 and w.getnchannels()==2 and w.getsampwidth()==2
    riser=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,2)/32768.
# Align the loudest 10ms of the supplied swell with the first scene cut,
# not a spoken word. Discard the trailing decay and silence at that cut.
gain=.28
block=480
energy=np.array([np.mean(riser[i:i+block]**2) for i in range(0,len(riser),block)])
crest_end=(int(np.argmax(energy))+1)*block
cut_seconds=report['click_flash_times'][0]
cut_sample=round(cut_seconds*48000)
offset_samples=cut_sample-crest_end
assert offset_samples>=0
used=riser[:crest_end].copy()
used[-48:]*=np.linspace(1,0,48)[:,None]  # 1ms de-click, not an early fadeout
effect=np.zeros_like(speech)
effect[offset_samples:cut_sample]=used*gain
assert not np.any(effect[cut_sample:])
mix=speech+effect
peak=float(np.abs(mix).max())
if peak>.95: mix*=.95/peak
wav=OUT/'mix.wav'
with wave.open(str(wav),'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
    w.writeframes((np.clip(mix,-1,1)*32767).astype('<i2').tobytes())
output=OUT/'03-setbacks-supplied-riser.mp4'
ass=BASE/'captions.ass'
hero=ROOT/'outputs/serhant-v2/03-hero-overlay.png'
graph=f"[0:v]subtitles=filename={ass}:fontsdir={ROOT/'backend/fonts'}[base];[base][2:v]overlay=0:0:enable='lt(t,3.6)'[v]"
run([FF,'-v','error','-y','-i',str(ROOT/'outputs/serhant-v4/03-setbacks-supplied-riser.mp4'),'-i',str(wav),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','128k','-movflags','+faststart',str(output)])
probe=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(output)]).stdout)
v=next(s for s in probe['streams'] if s['codec_type']=='video'); a=next(s for s in probe['streams'] if s['codec_type']=='audio')
assert (v['width'],v['height'])==(720,1280)
assert abs(float(v['duration'])-float(a['duration']))<.05
assert not run([FF,'-v','error','-i',str(output),'-f','null','-']).stderr.strip()
run([FF,'-v','error','-y','-ss','1.8','-i',str(output),'-frames:v','1',str(OUT/'review.jpg')])
result={'path':str(output),'duration':probe['format']['duration'],'bytes':output.stat().st_size,'riser_source_url':'https://youtube.com/shorts/KiJX7agcIns?is=cv6SPgpveVX0vniQ','riser_asset':str(asset),'riser_gain':gain,'riser_offset':offset_samples/48000,'riser_crest_end_and_scene_cut':cut_seconds,'riser_source_crest_end':crest_end/48000,'pitch_speed':'unchanged','rejected_generated_riser_clicks_flashes':'removed','full_decode':'passed','video_duration':v['duration'],'audio_duration':a['duration']}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
