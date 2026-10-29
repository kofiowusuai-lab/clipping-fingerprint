"""Install authored clipping rules into a NEW explicit Hermes home, safely.

Run with the fingerprint virtualenv Python; no credentials or old profile are copied.
"""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile-home',type=Path,required=True);p.add_argument('--dry-run',action='store_true');args=p.parse_args()
    home=args.profile_home.expanduser().resolve()
    if home.exists():p.error('Target already exists. Refusing to overwrite another profile; choose a fresh explicit directory.')
    if ROOT==home or home in ROOT.parents:p.error('Profile must not contain the repository')
    config={'command':sys.executable,'args':[str(ROOT/'scripts/fingerprint_mcp.py'),'--profile-home',str(home)],'timeout':240,'connect_timeout':60}
    if args.dry_run:
        print(json.dumps({'profileHome':str(home),'repository':str(ROOT),'mcp':config,'copiesCredentials':False},indent=2));return
    if not shutil.which('hermes'):p.error('Install Hermes first; see official documentation')
    home.mkdir(parents=True,mode=0o700)
    for name in ('SOUL.md','config.yaml'):shutil.copy2(ROOT/name,home/name)
    shutil.copytree(ROOT/'skills',home/'skills')
    env={**os.environ,'HERMES_HOME':str(home)}
    # Scope every config operation to this explicitly chosen new home.
    for key,value in [('terminal.cwd',str(ROOT)),('mcp_servers.supoclip',json.dumps(config))]:
        subprocess.run(['hermes','config','set',key,value],env=env,check=True)
    (home/'fingerprint.json').write_text(json.dumps({'repository':str(ROOT),'distribution':'clipping-fingerprint','version':'1.0.0'},indent=2))
    print(json.dumps({'installed':str(home),'configuredWorkingDirectory':str(ROOT),'next':'Use HERMES_HOME=<this path> hermes setup, then chat. Configure only your own credentials; no gateway was started.'},indent=2))
if __name__=='__main__':main()
