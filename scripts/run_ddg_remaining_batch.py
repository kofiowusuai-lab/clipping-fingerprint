"""Sequential bounded renders, with persistent progress. Delivery is reviewed separately."""
import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs/creator-engine/Vpd-xFMfCq0/five-clip-batch';p=O/'manifest.json';ids=[r['id'] for r in json.loads(p.read_text())][1:]
def update(ident,**data):
    rows=json.loads(p.read_text());next(r for r in rows if r['id']==ident).update(data);p.write_text(json.dumps(rows,indent=2))
for ident in ids:
    w=O/ident;update(ident,status='rendering')
    for label,cmd in [('graphics',[sys.executable,'scripts/creator_caption_band.py',str((w/'graphics-job.json').resolve())]),('render',[sys.executable,'scripts/render_ddg_batch_clip.py',str((w/'plan.json').resolve())])]:
        if label=='graphics' and (w/'graphics/manifest.json').exists():continue
        log=w/(label+'.log')
        with log.open('w') as f:r=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
        if r.returncode:
            update(ident,status='failed',failureStage=label,log=str(log));raise SystemExit(r.returncode)
    update(ident,status='awaiting-visual-review',file=str(w/'final.mp4'));print(ident,'ready for actual-output review',flush=True)
print('Remaining four exports completed technical QA',flush=True)
