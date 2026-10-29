"""Verify selected creator speech using only the cached local Whisper model."""
import json,sys
from pathlib import Path
import torch,whisper
R=Path(__file__).resolve().parents[1];O=R/'outputs/creator-engine/yHLNoTKOO4A'
torch.set_num_threads(2)
model=whisper.load_model(str(R/'.local/cache/whisper/tiny.en.pt'),device='cpu')
d=model.transcribe(str(O/'belt-source.wav'),word_timestamps=True,language='en',fp16=False,temperature=0)
d['source_offset_seconds']=1828.0;d['limitations']='Independent local ASR; manually review disagreements and visual context, not speaker diarization.'
(O/'belt-whisper.json').write_text(json.dumps(d,indent=2));print(d['text'],flush=True)
for s in d['segments']:
 for w in s.get('words',[]):print(round(1828+w['start'],3),round(1828+w['end'],3),w['word'],flush=True)
