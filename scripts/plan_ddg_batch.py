"""Source-grounded five-clip plans; caption order never changed by ASR timings."""
import json,math,re
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs/creator-engine/Vpd-xFMfCq0/five-clip-batch';p=O/'manifest.json';rows=json.loads(p.read_text());raw=json.loads((O.parent/'words.json').read_text())['words']
config={
'01-gym-tweet':{'ranges':[(676.733333,744.3)],'beats':[676.733333,694.0,705.6,714.9,719.2,729.4,744.3],'keywords':['tweet','stomach','fat','gym','8:00'],'copy':'One tweet had DDG in the gym at 8AM. 💀\n\nHe read the stomach comment and took it personally.\n\n#DDG #DDGLive #GymMotivation #StreamerClips #FunnyMoments'},
'02-recognised':{'ranges':[(4805.5,4838.1),(4841.0,4848.0),(4850.0,4851.35),(4853.36,4871.3)],'beats':[4805.5,4818.8,4828.3,4838.1,4841.0,4848.0,4850.0,4851.35,4853.36,4858.0,4863.8,4871.3],'keywords':['famous','mask','sunglasses','tat','eyes'],'copy':'The mask wasn’t enough. The sunglasses weren’t enough either. 😂\n\nDDG explains how fans still recognise him.\n\n#DDG #DDGLive #StreamerClips #CelebrityLife #FunnyMoments'},
'03-staged-argument':{'ranges':[(5904.166667,5955.55)],'beats':[5904.166667,5913.6,5924.2,5936.0,5943.8,5947.7,5955.55],'keywords':['argue','role','play','tripping','bad'],'hero':'DDG TRIED TO STAGE A CRASH-OUT 💀','copy':'DDG wanted to recreate the angry moment… his friend heard something completely different. 💀\n\n#DDG #DDGLive #StreamerClips #FunnyMoments #StreamHighlights'},
'04-budget':{'ranges':[(9870.0,9911.766667)],'beats':[9870.0,9877.6,9888.7,9893.6,9901.0,9906.0,9911.766667],'keywords':['Maldives','flamingo','Santa','Monica','Miami'],'copy':'The Maldives plan lasted until DDG realised he could find a flamingo closer to home. 💀\n\nA music-video brainstorm took a very practical turn.\n\n#DDG #DDGLive #MusicVideo #StreamerClips #FunnyMoments'},
'05-finances':{'ranges':[(8656.2,8700.733333)],'beats':[8656.2,8665.5,8676.8,8683.7,8686.1,8688.9,8694.4,8700.733333],'keywords':['South','Africa','moon','sun','finances'],'hero':'DDG: “I CAN AFFORD TO FLY TO THE SUN” 💀','copy':'DDG was explaining his travel budget… then space travel entered the conversation. 💀\n\n“Maybe not the sun.”\n\n#DDG #DDGLive #StreamerClips #FunnyMoments #MoneyTalk'}
}

def safe_crop(r,a,b,base):
    if base is not None:return base
    samples=json.loads((O/r['id']/'face-samples.json').read_text());fs=[s['box'] for s in samples if a<=s['time']<b and s['box'][2]>55 and s['box'][3]>70]
    if not fs:return [220,100,800,620]
    left=min(f[0] for f in fs);right=max(f[0]+f[2] for f in fs);width=min(1200,max(780,math.ceil((right-left+140)*1.12/2)*2));center=sorted(f[0]+f[2]/2 for f in fs)[len(fs)//2];margin=width*.06+25
    low=max(0,right+margin-width);high=min(1280-width,left-margin)
    x=max(0,min(1280-width,center-width/2))
    if low<=high:x=max(low,min(high,x))
    else:width=min(1280,math.ceil((right-left+100)/2)*2);x=max(0,min(1280-width,left-50))
    return [int(x)//2*2,100,int(width)//2*2,620]

for r in rows:
    z=config[r['id']];ranges=[(round(a*30)/30,round(b*30)/30) for a,b in z['ranges']];words=[];segments=[];cursor=0
    for a,b in ranges:
        count=round((b-a)*30);duration=count/30
        for word in raw:
            if a<=word['start']<b-.03:
                text=word['text'].upper()
                if text in ['MALDES,','MALDS','MALDES']:text='MALDIVES'+(',' if text.endswith(',') else '')
                if r['id']=='04-budget' and text=='PED':text='PET'
                if r['id']=='05-finances' and text=='ROAR':text='AURA'
                if r['id']=='02-recognised' and text in ['TAG.','TAG','HEAD']:
                    text={'TAG.':'TAT.','TAG':'TAT','HEAD':'HAND'}[text]
                start=cursor/30+word['start']-a;end=min(cursor/30+duration,cursor/30+word['end']-a,start+.85)
                if end>start:words.append({'text':text,'start':round(start,6),'end':round(end,6)})
        bounds=[a]+[round(t*30)/30 for t in z['beats'] if a<t<b]+[b]
        for i,(sa,sb) in enumerate(zip(bounds,bounds[1:])):
            browser=r['id']=='01-gym-tweet' and 705.6<=sa<714.9
            finance=r['id']=='05-finances'
            fixed=[30,90,240,160] if browser else ([20,90,260,165] if finance else None)
            crop=safe_crop(r,sa,sb,fixed);zooms=(1.0,1.0) if browser else ((1.0,1.07) if finance else ((1.0,1.12) if i%2==0 else (1.12,1.0)))
            if crop[2]>1000:zooms=(1.0,1.0)
            segments.append({'startFrame':cursor+round((sa-a)*30),'endFrame':cursor+round((sb-a)*30),'sourceStart':sa-r['archiveOffset'],'sourceEnd':sb-r['archiveOffset'],'archiveRange':[sa,sb],'crop':crop,'zoomStart':zooms[0],'zoomEnd':zooms[1],'tweetPanel':browser,'reason':'Reviewed actual source; face-detection bounds are framing cues, not identity/speaker labels.'})
        cursor+=count
    for i in range(len(words)-1):words[i]['end']=min(words[i]['end'],words[i+1]['start'])
    for word in words:word['end']=min(word['end'],cursor/30)
    words=[w for w in words if w['end']>w['start']]
    assert all(0<=w['start']<w['end']<=cursor/30+.00001 for w in words)
    assert all(segments[i]['endFrame']==segments[i+1]['startFrame'] for i in range(len(segments)-1))
    assert segments[0]['startFrame']==0 and segments[-1]['endFrame']==cursor
    hero=z.get('hero',r['hero']);job={'outputDir':str((O/r['id']/'graphics').resolve()),'fontPath':str(R/'backend/fonts/Poppins-ExtraBold.ttf'),'width':1080,'height':1920,'fps':30,'durationInFrames':cursor,'words':words,'headline':hero,'keywords':z['keywords'],'captionY':.80}
    plan={'id':r['id'],'source':r['source'],'archiveOffset':r['archiveOffset'],'archiveRanges':ranges,'width':1080,'height':1920,'fps':30,'durationInFrames':cursor,'segments':segments,'graphicsJob':job,'postCaption':z['copy'],'limitations':['720p source or embedded lower-resolution facecam upscaled; no reconstructed detail.','YouTube word times inferred and local tiny.en checked independently, not diarization/forced alignment.','No added music, SFX, stock assets or watermarks.']}
    if r['id']=='04-budget':plan['editorial']='Ends after local-location/flamingo payoff. Omitted the separate, context-dependent jealous-viewer music-video scene rather than padding the clip.'
    if r['id']=='02-recognised':plan['editorial']='Removed repetitive disparaging asides and one ambiguously transcribed line; retained actual recognition anecdote in original chronological order.'
    w=O/r['id'];(w/'plan.json').write_text(json.dumps(plan,indent=2));(w/'graphics-job.json').write_text(json.dumps(job,indent=2));(w/'post-caption.txt').write_text(z['copy']+'\n');r.update(hero=hero,seconds=cursor/30,frames=cursor,plan=str((w/'plan.json').resolve()),status='planned')
p.write_text(json.dumps(rows,indent=2));print(json.dumps([{'id':r['id'],'seconds':r['seconds'],'frames':r['frames'],'hero':r['hero']} for r in rows],indent=2))
