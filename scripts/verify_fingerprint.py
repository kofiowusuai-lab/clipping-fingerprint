"""Verify distributed renderer/style/font/skill bytes against fingerprint.lock.json."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 data=json.loads((ROOT/'fingerprint.lock.json').read_text());mismatches=[]
 for name,expected in data['sha256'].items():
  file=(ROOT/name).resolve()
  if not file.is_relative_to(ROOT) or not file.is_file():mismatches.append({'file':name,'issue':'missing/unsafe'});continue
  if hashlib.sha256(file.read_bytes()).hexdigest()!=expected:mismatches.append({'file':name,'issue':'modified'})
 print(json.dumps({'version':data['version'],'filesChecked':len(data['sha256']),'matches':not mismatches,'mismatches':mismatches,'note':'Integrity is not a guarantee of identical AI choices or cross-platform encoded pixels.'},indent=2));return 1 if mismatches else 0
if __name__=='__main__':raise SystemExit(main())
