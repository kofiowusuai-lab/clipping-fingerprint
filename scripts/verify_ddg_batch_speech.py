"""Independent local speech check for five bounded excerpts; no hosted calls."""
import json,time
from pathlib import Path
import torch,whisper
R=Path(__file__).resolve().parents[1];O=R/'outputs/creator-engine/Vpd-xFMfCq0/five-clip-batch'
torch.set_num_threads(2)
model=whisper.load_model(str(R/'.local/cache/whisper/tiny.en.pt'),device='cpu')
ids=[r['id'] for r in json.loads((O/'manifest.json').read_text())]
for ident in ids:
    w=O/ident; until=time.monotonic()+1200
    while not (w/'speech.wav').exists():
        if time.monotonic()>until:raise RuntimeError(f'No complete audio context for {ident}')
        time.sleep(2)
    if (w/'whisper.json').exists():continue
    result=model.transcribe(str(w/'speech.wav'),word_timestamps=True,language='en',fp16=False,temperature=0)
    (w/'whisper.json').write_text(json.dumps(result,indent=2));(w/'speech-check.txt').write_text(result['text']);print(ident,result['text'],flush=True)
