"""Normalize YouTube's word-offset captions for review, without hosted AI."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'.local/uploads/youtube-cache/Q-DFC0AnbY4'
d=json.loads((p/'full.en-orig.json3').read_text())
words=[]
for e in d['events']:
    if e.get('aAppend') or not e.get('segs'):continue
    for seg in e['segs']:
        text=seg.get('utf8','').strip()
        if not text:continue
        start=e['tStartMs']+seg.get('tOffsetMs',0)
        words.append({'text':text,'start':start,'event_end':e['tStartMs']+e.get('dDurationMs',0),'speaker':None})
words.sort(key=lambda w:w['start'])
for i,w in enumerate(words):
    next_start=words[i+1]['start'] if i+1<len(words) else w['event_end']
    w['end']=max(w['start']+20,min(next_start,w['start']+1000,w.pop('event_end')))
cache={'version':2,'words':words,'utterances':[],'text':' '.join(w['text'] for w in words),'language_code':'en','source':'YouTube automatic captions; verify chosen cuts locally'}
(p/'full.transcript_cache.json').write_text(json.dumps(cache))
lines=[]
for t in range(0,5295,15):
    s=' '.join(w['text'] for w in words if t*1000<=w['start']<(t+15)*1000)
    lines.append(f'{t//3600:02d}:{t//60%60:02d}:{t%60:02d} [{t}-{t+15}] {s}')
(p/'transcript-review.txt').write_text('\n'.join(lines))
print(json.dumps({'words':len(words),'review_path':str(p/'transcript-review.txt')}))
