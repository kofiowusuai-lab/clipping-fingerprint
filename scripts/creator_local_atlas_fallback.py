"""Local-font atlas fallback when Chrome cannot launch; no media/ASR fabrication."""
import json,math,re,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter
R=Path(__file__).resolve().parents[1];job=json.loads(Path(sys.argv[1]).read_text());root=Path(job['outputDir']);root.mkdir(exist_ok=False)
width,height=job['width'],job['height'];font=ImageFont.truetype(job['fontPath'],round(width*.078));stroke=round(width*.006);cell=200
key=lambda t:re.sub(r'[^\w]','',t.lower());keywords={key(t) for t in job['keywords']};sprites=[];indices={};words=[];pages=[]
for word in job['words']:
    color='#d8ff36' if key(word['text']) in keywords else '#ffffff';k=(word['text'],color)
    if k not in indices:indices[k]=len(sprites);sprites.append({'text':word['text'],'color':color})
    words.append({**word,'sprite':indices[k]})
for a in range(0,len(sprites),10):
    batch=sprites[a:a+10];im=Image.new('RGBA',(width,cell*len(batch)));d=ImageDraw.Draw(im);page=root/f'atlas-{len(pages):04d}.png'
    for i,s in enumerate(batch):
        f=font;box=d.textbbox((0,0),s['text'],font=f,stroke_width=stroke)
        if box[2]-box[0]>width*.80:f=ImageFont.truetype(job['fontPath'],int(font.size*width*.80/(box[2]-box[0])))
        d.text((width/2,i*cell+cell/2),s['text'],font=f,anchor='mm',fill=s['color'],stroke_width=stroke,stroke_fill='#101014')
        s.update(page=str(page),x=0,y=i*cell,width=width,height=cell)
    im.save(page);pages.append(str(page))
hero=Image.new('RGBA',(width,height));d=ImageDraw.Draw(hero);hf=ImageFont.truetype(job['fontPath'],round(width*.074));text=job['headline'];emoji='💀' if '💀' in text else '';text=text.replace('💀','').strip();lines=[];line=''
for token in text.split():
    candidate=(line+' '+token).strip()
    if d.textlength(candidate,font=hf)>width*.86 and line:lines.append(line);line=token
    else:line=candidate
if line:lines.append(line)
lineheight=round(hf.size*1.12);total=len(lines)*lineheight+(85 if emoji else 0);top=height*.15-total/2
for i,line in enumerate(lines):d.text((width/2,top+i*lineheight+lineheight/2),line,font=hf,anchor='mm',fill='white',stroke_width=stroke,stroke_fill='#101014')
if emoji:
    # Use the machine's existing emoji font; do not draw a fake missing-glyph box.
    ef=ImageFont.truetype('/System/Library/Fonts/Apple Color Emoji.ttc',109);e=Image.new('RGBA',(150,150));ed=ImageDraw.Draw(e);ed.text((75,75),emoji,font=ef,anchor='mm',embedded_color=True);box=e.getbbox();assert box;e=e.crop(box);e.thumbnail((80,80));hero.alpha_composite(e,(round((width-e.width)/2),round(top+len(lines)*lineheight)))
hero.save(root/'hero.png')
data={'version':1,'kind':'creator-static-atlas-local-font-fallback','width':width,'height':height,'fps':job['fps'],'durationInFrames':job['durationInFrames'],'captionY':job['captionY'],'cellHeight':cell,'words':words,'sprites':sprites,'pages':pages,'heroPath':str(root/'hero.png'),'browserCaptures':0,'provenance':'Real Poppins/Apple Color Emoji glyphs locally rasterized because Chrome startup timed out; not synthetic tool output.'};(root/'atlas-manifest.json').write_text(json.dumps(data,indent=2))
sys.path.insert(0,str(R/'scripts'));from creator_caption_band import generate;print(json.dumps(generate(root/'atlas-manifest.json')))
