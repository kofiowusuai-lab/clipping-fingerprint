"""Build reviewable local timing corrections without replacing the original source cache."""
import difflib,json,re
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs/premium-dana'
d=json.loads((R/'.local/uploads/youtube-cache/Q-DFC0AnbY4/full.transcript_cache.json').read_text())
words=d['words'];edits=[]
for w in words:
 if 677600<=w['start']<=677800 and w['text']=='Bad':w['end']=678040
words.append({'text':'shit','start':678040,'end':678280,'speaker':None});words.sort(key=lambda w:w['start'])
# Preserve text, use independently decoded local audio to refine matched word timing.
norm=lambda s:re.sub('[^a-z0-9]','',s.lower())
v=json.loads((O/'quit-drinking-whisper.json').read_text());a=v['source_start']
local=[{'text':w['word'].strip(),'start':round((a+w['start'])*1000),'end':round((a+w['end'])*1000)} for s in v['segments'] for w in s.get('words',[]) if w['end']>w['start']]
subset=[w for w in words if 241100<=w['start']<267050]
local=[w for w in local if w['start']>=241100]
matcher=difflib.SequenceMatcher(a=[norm(w['text']) for w in subset],b=[norm(w['text']) for w in local],autojunk=False)
anchors={}
for block in matcher.get_matching_blocks():
 for k in range(block.size):anchors[block.a+k]=local[block.b+k]
for i,w in enumerate(subset):
 old=[w['start'],w['end']]
 if i in anchors:w.update({k:anchors[i][k] for k in ['start','end']})
 else:
  left=max((j for j in anchors if j<i),default=None);right=min((j for j in anchors if j>i),default=None)
  lo=anchors[left]['end'] if left is not None else w['start'];hi=anchors[right]['start'] if right is not None else w['end']
  run=[j for j in range((left+1) if left is not None else 0,right if right is not None else len(subset)) if j not in anchors]
  if left is not None and right is not None and hi>lo and run:
   pos=run.index(i);w['start']=round(lo+(hi-lo)*pos/len(run));w['end']=round(lo+(hi-lo)*(pos+1)/len(run))
 if old!=[w['start'],w['end']]:edits.append({'text':w['text'],'original_ms':old,'refined_ms':[w['start'],w['end']]})
# Preserve source token order even where an independent decoder omitted fillers.
# Resolve tiny JSON3 overlaps and anchor/filler overlap explicitly, retaining text.
normalization=[]
for i,w in enumerate(words):
 if i and w['start']<=words[i-1]['start']:
  old=w['start'];w['start']=words[i-1]['start']+10;normalization.append({'index':i,'text':w['text'],'old_start':old,'start':w['start']})
for i,w in enumerate(words):
 original=w['end'];w['end']=max(w['start']+1,min(w['end'],words[i+1]['start'] if i+1<len(words) else w['end']))
 if original!=w['end']:normalization.append({'index':i,'text':w['text'],'old_end':original,'end':w['end']})
d['words']=words;d['timing_review']='Sobriety selected matched words refined with cached local tiny.en; unmatched fillers interpolated between anchors, not forced alignment. Original text preserved. Known omitted profanity restored from prior audio verification.'
(O/'timestamp-normalization.json').write_text(json.dumps(normalization,indent=2))
(O/'reviewed-source-transcript.json').write_text(json.dumps(d,indent=2));(O/'transcript-timing-edits.json').write_text(json.dumps(edits,indent=2));print(len(edits),'timing refinements; full source cache preserved')
