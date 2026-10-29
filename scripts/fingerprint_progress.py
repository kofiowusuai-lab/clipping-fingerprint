"""Local progress records for portable Hermes clipping installs; no fixed routes."""
import argparse,json,uuid,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--state-dir',type=Path,default=ROOT/'outputs/task-monitors');s=p.add_subparsers(dest='cmd',required=True)
 a=s.add_parser('start');a.add_argument('title');a.add_argument('--stages',default='Source,Select,Render,QA,Deliver')
 a=s.add_parser('stage');a.add_argument('id');a.add_argument('stage');a.add_argument('status',choices=['pending','active','done','failed']);a.add_argument('--detail',default='')
 a=s.add_parser('note');a.add_argument('id');a.add_argument('note')
 a=s.add_parser('show');a.add_argument('id')
 a=s.add_parser('finish');a.add_argument('id');g=a.add_mutually_exclusive_group(required=True);g.add_argument('--success',action='store_true');g.add_argument('--fail',action='store_true');a.add_argument('--summary',required=True)
 args=p.parse_args();args.state_dir.mkdir(parents=True,exist_ok=True)
 if args.cmd=='start':
  id='tm_'+uuid.uuid4().hex[:12];data={'id':id,'title':args.title,'transport':'local','closed':False,'stages':{name.strip():{'status':'pending'} for name in args.stages.split(',')},'notes':[]}
 else:
  id=args.id
  if not id.startswith('tm_') or not id[3:].isalnum():p.error('Invalid monitor id')
  data=json.loads((args.state_dir/(id+'.json')).read_text())
 if args.cmd=='stage':
  if args.stage not in data['stages']:p.error('Unknown stage')
  data['stages'][args.stage]={'status':args.status,'detail':args.detail}
 elif args.cmd=='note':data['notes'].append(args.note)
 elif args.cmd=='finish':data.update(closed=True,result='success' if args.success else 'failed',summary=args.summary)
 if args.cmd!='show':
  out=args.state_dir/(id+'.json');temp=out.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2));os.chmod(temp,0o600);temp.replace(out)
 print(id if args.cmd=='start' else json.dumps(data,indent=2))
if __name__=='__main__':main()
