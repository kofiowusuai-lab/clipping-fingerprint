"""Launch self-hosted SupoClip MCP with this install's own secrets only."""
import os,sys
from pathlib import Path
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[1]
def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile-home',type=Path)
    args=parser.parse_args()
    home=str(args.profile_home.expanduser().resolve()) if args.profile_home else os.environ.get('HERMES_HOME')
    if not home:raise SystemExit('Pass --profile-home or set HERMES_HOME to your own Hermes profile')
    os.environ['HERMES_HOME']=home
    # This path is configured explicitly in the Hermes MCP command, so no credentials
    # need to be copied into the MCP config. Values are never printed.
    for file in (ROOT/'.env',ROOT/'.env.local',Path(home).expanduser()/'.env'):
        if not file.is_file():continue
        for key,value in dotenv_values(file).items():
            if value is not None and (key.startswith('SUPOCLIP_') or key=='BACKEND_AUTH_SECRET'):
                os.environ.setdefault(key,value)
    os.environ.setdefault('SUPOCLIP_API_URL','http://127.0.0.1:8000')
    os.environ.setdefault('SUPOCLIP_DOWNLOAD_DIR',str(ROOT/'outputs'))
    if os.environ.get('BACKEND_AUTH_SECRET'):
        os.environ.setdefault('SUPOCLIP_AUTH_SECRET',os.environ['BACKEND_AUTH_SECRET'])
    sys.path.insert(0,str(ROOT/'mcp/src'))
    from supoclip_mcp.server import main as serve
    serve()
if __name__=='__main__':main()
