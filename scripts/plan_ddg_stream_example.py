"""Reviewed DDG stream example; timing evidence is not automatic highlight approval."""
import copy
import difflib
import json
import re
from pathlib import Path
from typing import Any

R = Path(__file__).resolve().parents[1]
O = R / 'outputs/creator-engine/Vpd-xFMfCq0'
S = R / '.local/uploads/youtube-cache/Vpd-xFMfCq0/phone-context.mp4'
start, end, fps, archive_offset = 24.08, 88.455, 24, 765
n = round((end-start)*fps)
raw = json.loads((O/'words.json').read_text())['words']
words = [dict(text=w['text'], start=w['start']-archive_offset, end=w['end']-archive_offset) for w in raw if start <= w['start']-archive_offset < end-.04]
asr = json.loads((O/'phone-whisper.json').read_text())
verified = [w for s in asr['segments'] for w in s.get('words', []) if start <= w['start'] < end]
key = lambda t: re.sub(r'[^a-z0-9]', '', t.lower())
# Retain the original caption order. Independent tiny.en is a speech/omission check,
# not a forced aligner: mixing its word starts with unmatched cache starts can reorder words.
# The first audible onset is independently established by the local excerpt.
if words and words[0]['text'].lower() == 'cheating':
    words[0]['start'] = 24.20
# YouTube display captions omitted audible words independently present in the local ASR.
words += [dict(text='N****', start=27.40, end=27.86), dict(text='SHIT', start=60.60, end=60.76), dict(text='FUCK', start=75.66, end=75.80), dict(text='SHIT.', start=85.00, end=85.28)]
words.sort(key=lambda w:w['start'])
for i,w in enumerate(words):
    limit = words[i+1]['start'] if i+1 < len(words) else end
    w['end'] = min(w['end'], limit, w['start']+.85, end)
words = [w for w in words if w['end'] > w['start']]
for w in words:
    w.update(text=w['text'].upper(), start=round(w['start']-start,6), end=round(min(n/fps,w['end']-start),6))
assert all(0<=w['start']<w['end']<=n/fps for w in words)
# Broad source-supported windows protect both the phone and the leftward lean.
bounds = [start,54.8,64.1,end]
crops = [[300,120,650,600],[220,120,700,600],[300,120,650,600]]
shots = [dict(startFrame=round((a-start)*fps), endFrame=round((b-start)*fps), crop=crop, reviewed=True, sourceRange=[archive_offset+a,archive_offset+b], emphasisZoom=False, reason='Actual phone/hand action and leftward lean inspected in source contact sheet; no speaker-ID claim.') for a,b,crop in zip(bounds,bounds[1:],crops)]
plan: dict[str, Any] = dict(version=1, source=str(S), sourceUrl='https://www.youtube.com/watch?v=Vpd-xFMfCq0', sourceWidth=1280, sourceHeight=720, start=start,end=end,width=1080,height=1920,fps=fps,fontPath=str(R/'backend/fonts/Poppins-ExtraBold.ttf'),outputDir=str(O/'cheaters-need-gloves-corrected'),contentType='Creator livestream: spoken joke plus physical phone demonstration',shots=shots,words=words,graphics={'caption':{'position':.80,'maxWords':1},'headline':{'text':'DDG SAYS CHEATERS NEED GLOVES 💀','start':0,'end':2.4,'x':.5,'y':.15,'color':'#FFFFFF','fontSizeRatio':.074},'emphasis':{'keywords':['cheating','harder','touch','gloves','thumb','slap']}},editorial={'archiveRange':[archive_offset+start,archive_offset+end],'opening':'Cheating has got harder.','setup':'DDG explains Touch ID and includes his not-saying-I-cheat disclaimer.','visualContext':'Actual phone unlock, finger demonstration, and physical performance of hypothetical discovery retained.','payoff':'Waking up to a slap and a crying partner; closes on You do not want that.','pacing':'Continuous source exchange; demonstration pauses retained for the visible action, no unrelated stream-delay chatter.','limitations':['720p source excerpt upscaled to 1080x1920; no claim of recovered native detail.','Phone brand/model discussion is the streamer’s own comedic commentary, not a verified technology review.','Local tiny.en and YouTube inferred timestamps cross-checked; no diarization.','Caption-only masking of one slur; original source audio not censored.','No music or sound effects added.']},postCaption='DDG turned a phone review into a warning for cheaters. 💀\n\nThe gloves explanation took a turn.\n\n#DDG #DDGLive #StreamerClips #FunnyMoments #StreamHighlights')
(O/'clip-plan.json').write_text(json.dumps(plan,indent=2))
print(json.dumps({'frames':n,'seconds':n/fps,'captionWords':len(words),'archiveRange':plan['editorial']['archiveRange'],'opening':[w['text'] for w in words[:8]],'closing':[w['text'] for w in words[-8:]]},indent=2))
