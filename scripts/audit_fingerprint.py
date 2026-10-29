"""Audit exactly the files Git would publish, without printing secret values."""
import argparse,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATTERNS=[('GitHub token',re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}')),('Telegram token',re.compile(rb'\b[0-9]{8,12}:[A-Za-z0-9_-]{30,}')),('OpenAI token',re.compile(rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}')),('private key',re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'))]
def audit(secret_files=(), forbidden=()):
    tracked=subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT,capture_output=True,check=True).stdout.decode().split('\0');files=sorted(set(filter(None,tracked)));issues=[];known=[]
    if secret_files:
        from dotenv import dotenv_values
        for path in secret_files:
            for key,value in dotenv_values(path).items():
                if value and len(value)>=16 and re.search(r'(TOKEN|SECRET|API_KEY|PASSWORD|ENCRYPTION_KEY)$',key):known.append(value.encode())
    for name in files:
        p=ROOT/name
        if p.is_symlink():issues.append({'file':name,'issue':'symlink forbidden in publish set'});continue
        if not p.is_file():continue
        parts=Path(name).parts
        if p.name in ('.env','auth.json','state.db','config.local.yaml') or any(k in parts for k in ('node_modules','.venv','memories','sessions','outputs','.local')):issues.append({'file':name,'issue':'private/runtime path'});continue
        if p.suffix in ('.mp4','.wav','.mp3','.onnx','.db'):
            import hashlib
            licensed_yunet=(name=='backend/src/media/models/face_detection_yunet_2023mar.onnx' and hashlib.sha256(p.read_bytes()).hexdigest()=='8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4')
            if not licensed_yunet:issues.append({'file':name,'issue':'media/model/runtime binary'});continue
        data=p.read_bytes()
        if b'\0' in data[:4096]:continue # fonts/images; not credential documents
        for label,pattern in PATTERNS:
            if pattern.search(data):issues.append({'file':name,'issue':label+' pattern'})
        if any(value in data for value in known):issues.append({'file':name,'issue':'matches supplied local secret value'})
        if any(value.encode() in data for value in forbidden):issues.append({'file':name,'issue':'operator-supplied forbidden identity/path'})
    return {'filesChecked':len(files),'suppliedSecretFiles':len(secret_files),'issues':issues,'passed':not issues}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--secret-file',type=Path,action='append',default=[]);p.add_argument('--forbid-text',action='append',default=[],help='Reject operator-supplied private identifiers without embedding them in source');args=p.parse_args();r=audit(args.secret_file,args.forbid_text);print(json.dumps(r,indent=2));raise SystemExit(0 if r['passed'] else 1)
