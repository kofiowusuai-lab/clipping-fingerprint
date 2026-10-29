"""Non-billable live verification of native API, signed MCP, and queued worker."""
from pathlib import Path
import asyncio
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from dotenv import dotenv_values
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
ENV = dotenv_values(ROOT / '.env.local')
sys.path.insert(0, str(ROOT / 'backend'))
os.environ.update({k: v for k, v in ENV.items() if v is not None})


def signed(ts=None, secret=None):
    ts = str(ts or int(time.time()))
    uid = ENV['SUPOCLIP_USER_ID']
    sig = hmac.new((secret or ENV['BACKEND_AUTH_SECRET']).encode(), f'{uid}:{ts}'.encode(), hashlib.sha256).hexdigest()
    return {'x-supoclip-user-id': uid, 'x-supoclip-ts': ts, 'x-supoclip-signature': sig}


async def main():
    report = {}
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000', timeout=20) as client:
        for path in ['/health', '/health/db', '/health/redis']:
            r = await client.get(path)
            assert r.status_code == 200, path
            report[path] = r.json()
        for label, headers in [('missing', {}), ('unsigned', {'x-supoclip-user-id': ENV['SUPOCLIP_USER_ID']}),
                               ('bad_signature', signed(secret='not-the-secret')), ('expired', signed(ts=int(time.time())-1000)),
                               ('valid_signed', signed())]:
            r = await client.get('/tasks/', headers=headers)
            assert r.status_code == (200 if label == 'valid_signed' else 401), (label, r.status_code)
            report['auth_' + label] = r.status_code
    from arq import create_pool
    from arq.connections import RedisSettings
    pool = await create_pool(RedisSettings(host=ENV['REDIS_HOST'], port=int(ENV['REDIS_PORT']), password=ENV['REDIS_PASSWORD']))
    heartbeat = await pool.get('supoclip_tasks:health-check')
    assert heartbeat, 'Worker heartbeat absent'
    log_path = ROOT / '.local/logs/worker.log'
    log_offset = log_path.stat().st_size
    job = await pool.enqueue_job('cron:cleanup_media', _queue_name='supoclip_tasks', _job_id='local-smoke-' + uuid.uuid4().hex)
    # Cron jobs deliberately keep no result; assert the fresh success event.
    deadline = time.monotonic() + 30
    while True:
        with log_path.open() as log:
            log.seek(log_offset)
            recent = log.read()
        if '← cron:cleanup_media' in recent or '\\u2190 cron:cleanup_media' in recent:
            break
        assert time.monotonic() < deadline, 'No worker cleanup success event'
        await asyncio.sleep(0.2)
    report['worker_queue_job'] = {'id': job.job_id, 'function': 'cron:cleanup_media', 'completed': True}
    report['worker_heartbeat'] = heartbeat.decode()
    await pool.aclose()
    params = StdioServerParameters(command=str(ROOT / 'backend/.venv/bin/python'),
                                   args=[str(ROOT / 'scripts/local_runtime.py'), 'mcp'], cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            report['mcp_tools_count'] = len(tools.tools)
            for name in ['supoclip_health', 'supoclip_list_tasks', 'supoclip_billing_summary', 'supoclip_list_fonts']:
                r = await session.call_tool(name, {})
                assert not r.isError, (name, r)
                text = '\n'.join(c.text for c in r.content if c.type == 'text')
                assert not text.startswith('Error'), (name, text)
                report[name] = json.loads(text)
    # Authentication/model metadata only. This does not invoke an inference job.
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get('https://api.openai.com/v1/models/gpt-4.1-mini', headers={'Authorization': 'Bearer ' + ENV['OPENAI_API_KEY']})
        report['openai_nonbillable_model_lookup'] = {'status': r.status_code, 'inference_tested': False}
        if r.status_code == 200:
            report['openai_nonbillable_model_lookup']['model'] = r.json().get('id')
        else:
            report['openai_nonbillable_model_lookup']['error_type'] = r.json().get('error', {}).get('type')
            report['openai_nonbillable_model_lookup']['error_code'] = r.json().get('error', {}).get('code')
    (ROOT / '.local/verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
