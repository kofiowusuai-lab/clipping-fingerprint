#!/usr/bin/env python3
"""Manage the localhost-only native SupoClip API/worker, or run signed MCP.
Run with backend/.venv/bin/python scripts/local_runtime.py {start,status,stop,mcp}.
Docker dependencies: docker-compose --env-file .env.local -f compose.local-infra.yml up -d --wait
"""
from pathlib import Path
import os
import signal
import subprocess
import sys
import time
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.local'
PYTHON = ROOT / 'backend/.venv/bin/python'
SERVICES = {
    'api': ['-m', 'uvicorn', 'src.main:app', '--host', '127.0.0.1', '--port', '8000'],
    'worker': ['-m', 'arq', 'src.workers.tasks.WorkerSettings'],
}

def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if action == 'mcp':
        env = os.environ.copy()
        env.update({k: v for k, v in dotenv_values(ROOT / '.env.mcp.local').items() if v is not None})
        env['PYTHONPATH'] = str(ROOT / 'mcp/src')
        os.chdir(ROOT)
        os.execve(str(PYTHON), [str(PYTHON), '-m', 'supoclip_mcp.server'], env)
    if action not in {'start', 'stop', 'status'}:
        raise SystemExit('Expected start, stop, status, or mcp')
    for name, args in SERVICES.items():
        pidfile = STATE / f'{name}.pid'
        pid = int(pidfile.read_text()) if pidfile.exists() else None
        running = pid is not None and alive(pid)
        if action == 'start' and not running:
            if name == 'worker':
                # The API applies migrations; avoid run-at-startup cron racing it.
                import urllib.request
                deadline = time.monotonic() + 120
                while True:
                    try:
                        with urllib.request.urlopen('http://127.0.0.1:8000/health/db', timeout=3) as r:
                            if r.status == 200:
                                break
                    except Exception:
                        if time.monotonic() >= deadline:
                            raise SystemExit('API/migrations not ready; inspect .local/logs/api.log')
                        time.sleep(1)
            env = os.environ.copy()
            env.update({k: v for k, v in dotenv_values(ROOT / '.env.local').items() if v is not None})
            env['SUPOCLIP_SERVICE'] = name
            with (STATE / 'logs' / f'{name}.log').open('ab') as log:
                p = subprocess.Popen([str(PYTHON), *args], cwd=ROOT / 'backend', env=env,
                                     stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                     start_new_session=True)
            pid = p.pid
            pidfile.write_text(str(pid) + '\n')
            time.sleep(2)
            running = p.poll() is None
        elif action == 'stop' and running:
            assert pid is not None
            os.kill(pid, signal.SIGTERM)
            print(f'{name}: sent SIGTERM to {pid}')
            continue
        print(f'{name}: {"running" if running else "stopped"}; PID={pid}; log={STATE / "logs" / (name + ".log")}')

if __name__ == '__main__':
    main()
