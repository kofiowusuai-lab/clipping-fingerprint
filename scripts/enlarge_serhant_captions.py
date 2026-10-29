"""Enlarge captions from the clean picture; preserve approved audio and FX."""
import json
import re
import subprocess
import sys
from pathlib import Path
import imageio_ffmpeg
from PIL import ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/serhant-v7'; OUT.mkdir(exist_ok=True)
FONT=ImageFont.truetype(str(ROOT/'backend/fonts/Poppins-ExtraBold.ttf'),72)
source=(ROOT/'outputs/serhant-v3/captions.ass').read_text()
source=source.replace('Style: Main,Poppins ExtraBold,60,','Style: Main,Poppins ExtraBold,72,')
lines=[]; widths=[]; wraps=0
for line in source.splitlines():
    if line.startswith('Dialogue:'):
        fields=line.split(',',9); text=fields[9]
        visible=re.sub(r'\{[^}]*\}','',text)
        width=FONT.getlength(visible)
        if width>620:
            tokens=re.findall(r'(?:\{[^}]*\})*[^{} ]+',text)
            # Every caption token carries its own active-word colour; a line
            # break preserves timing/highlighting and keeps text off the edges.
            candidates=[]
            for k in range(1,len(tokens)):
                a=' '.join(tokens[:k]); b=' '.join(tokens[k:])
                wa=FONT.getlength(re.sub(r'\{[^}]*\}','',a)); wb=FONT.getlength(re.sub(r'\{[^}]*\}','',b))
                candidates.append((max(wa,wb),a+r'\N'+b))
            if candidates:
                width,text=min(candidates,key=lambda x:x[0]); wraps+=1
                fields[9]=text; line=','.join(fields)
        widths.append(width)
    lines.append(line)
assert max(widths)<660,max(widths)
ass=OUT/'captions-72.ass'; ass.write_text('\n'.join(lines)+'\n')
ff=imageio_ffmpeg.get_ffmpeg_exe()
base=OUT/'larger-captions-clean.mp4'
hero=ROOT/'outputs/serhant-v2/03-hero-overlay.png'
audio_source=ROOT/'outputs/serhant-v6/03-setbacks-white-luma-flash.mp4'
graph=f"[0:v]subtitles=filename={ass}:fontsdir={ROOT/'backend/fonts'}[base];[base][2:v]overlay=0:0:enable='lt(t,3.6)'[v]"
subprocess.run([ff,'-v','error','-y','-i',str(ROOT/'outputs/serhant-v3/picture.mp4'),'-i',str(audio_source),'-i',str(hero),'-filter_complex',graph,'-map','[v]','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','19','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(base)],check=True)
subprocess.run([sys.executable,str(ROOT/'scripts/add_white_luma_flash.py'),'--source',str(base),'--output-dir',str(OUT),'--output-name','03-setbacks-bigger-captions.mp4'],check=True)
final=OUT/'03-setbacks-bigger-captions.mp4'
# Read back the actual export, not just the ASS layout, for visual review.
subprocess.run([ff,'-v','error','-y','-ss','1.8','-i',str(final),'-frames:v','1',str(OUT/'caption-review.jpg')],check=True)
subprocess.run([ff,'-v','error','-y','-ss','18','-i',str(final),'-frames:v','1',str(OUT/'caption-review-18.jpg')],check=True)
def audio_hash(path):
    return subprocess.run([ff,'-v','error','-i',str(path),'-map','0:a:0','-c','copy','-f','hash','-hash','sha256','-'],capture_output=True,text=True,check=True).stdout.strip()
assert audio_hash(audio_source)==audio_hash(final)
print(json.dumps({'path':str(final),'font':'Poppins ExtraBold','old_size':60,'new_size':72,'max_caption_line_width':max(widths),'wrapped_dialogue_events':wraps,'approved_audio':'packet hash identical'},indent=2))
