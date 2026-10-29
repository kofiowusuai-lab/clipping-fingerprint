"""Profile-local Telegram clip delivery with receipts and explicit failure.

No shared Hermes changes. Token is read only from this profile's secret .env.
URLs containing it travel to curl via stdin, never process args or logs.
"""
import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from dotenv import dotenv_values

if not os.environ.get('HERMES_HOME'):
    raise RuntimeError('Set HERMES_HOME to your own clipping profile before delivery')
HOME=Path(os.environ['HERMES_HOME']).expanduser().resolve()
STATE=HOME/'delivery'; STATE.mkdir(mode=0o700,exist_ok=True)

class DeliveryError(Exception):
    def __init__(self,code,detail='',retry_after=0):
        self.code=code; self.detail=detail; self.retry_after=retry_after
        super().__init__(f'{code}: {detail}')

class TelegramDelivery:
    def __init__(self,token=None,call=None,sleep=time.sleep):
        self.token=token or dotenv_values(HOME/'.env').get('TELEGRAM_BOT_TOKEN')
        if not self.token: raise DeliveryError('missing_profile_token')
        self.transport=call or self._curl
        self.sleep=sleep

    def _curl(self,method,fields=None,file=None):
        # Fresh, hostname-verified IPv4 HTTP/1.1 connection for each request.
        config='url = '+json.dumps('https://api.telegram.org/bot'+self.token+'/'+method)+'\n'
        args=['/usr/bin/curl','--config','-','--silent','--show-error','--ipv4','--http1.1',
              '--connect-timeout','25','--max-time','240','--speed-limit','512','--speed-time','90']
        for key,value in (fields or {}).items():
            args+=['--form-string',f'{key}={value}']
        if file:
            key,path=file
            # Fixed safe upload name avoids curl multipart filename parsing issues.
            args+=['--form',f'{key}=@"{str(path).replace(chr(34),chr(92)+chr(34))}";filename=clip.mp4;type=video/mp4']
        p=subprocess.run(args,input=config.encode(),capture_output=True,timeout=250)
        if p.returncode:
            # Do not log raw curl errors: they can contain credential-bearing URLs.
            raise DeliveryError('transport_error',f'curl_exit={p.returncode}')
        try: response=json.loads(p.stdout)
        except (ValueError,TypeError): raise DeliveryError('invalid_api_response')
        if not response.get('ok'):
            detail=str(response.get('description',''))[:250].replace(self.token,'[redacted]')
            raise DeliveryError('telegram_'+str(response.get('error_code','error')),detail,response.get('parameters',{}).get('retry_after',0))
        return response['result']

    def _retry(self,method,fields=None,file=None,attempts=3):
        last=None
        for attempt in range(attempts):
            try: return self.transport(method,fields,file)
            except DeliveryError as e:
                last=e
                if e.code in ['telegram_400','telegram_401','telegram_403','telegram_413']: break
                if attempt+1<attempts:self.sleep(min(90,e.retry_after or (2**attempt)*2))
        raise last

    def health(self):
        bot=self._retry('getMe')
        return {'ok':True,'bot_id':bot['id'],'username':bot.get('username')}

    def send(self,path,chat_id,caption='',force=False):
        path=Path(path).expanduser().resolve()
        if not path.is_file(): raise DeliveryError('missing_file')
        if path.stat().st_size>49*1024*1024:raise DeliveryError('file_too_large','Export below 49 MiB before sending.')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        key=hashlib.sha256((str(chat_id)+':'+digest).encode()).hexdigest()
        receipt_file=STATE/(key+'.json')
        pending_file=STATE/(key+'.pending.json')
        # Serialise all uploads across gateway/script processes, not just per file.
        with (STATE/'send.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            if receipt_file.exists() and not force:
                previous=json.loads(receipt_file.read_text())
                remote=self._retry('getFile',{'file_id':previous['file_id']})
                if (remote['file_unique_id']==previous['file_unique_id']
                        and remote.get('file_size')==previous.get('remote_bytes')):
                    previous.update(status='confirmed',remote_readback=True,confirmed_at=time.time())
                    self._save(receipt_file,previous)
                    pending_file.unlink(missing_ok=True)
                    return {**previous,'already_confirmed':True}
                raise DeliveryError('remote_file_mismatch')
            probe=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],capture_output=True,text=True,check=True)
            data=json.loads(probe.stdout)
            video=next((s for s in data['streams'] if s['codec_type']=='video'),None)
            if not video or video.get('codec_name')!='h264':raise DeliveryError('unsupported_video','Use H.264 MP4 for native playback.')
            job={'path':str(path),'chat_id':str(chat_id),'sha256':digest,'caption':caption,'status':'pending','created_at':time.time()}
            self._save(pending_file,job)
            fields={'chat_id':str(chat_id),'caption':caption[:1024],'supports_streaming':'true','width':video['width'],'height':video['height'],'duration':int(float(data['format']['duration'])+.5)}
            message=None; mode=None; last=None
            for api,media_key in [('sendVideo','video'),('sendDocument','document')]:
                try:
                    payload=fields if media_key=='video' else {'chat_id':str(chat_id),'caption':caption[:1024],'disable_content_type_detection':'true'}
                    message=self._retry(api,payload,(media_key,path))
                    # Persist the acknowledged message BEFORE readback, so a readback
                    # outage cannot trigger another upload on the next invocation.
                    media=message.get(media_key)
                    if not media or str(message.get('chat',{}).get('id'))!=str(chat_id):
                        raise DeliveryError('invalid_delivery_receipt')
                    mode=media_key
                    ack={**job,'status':'accepted','message_id':message['message_id'],'file_id':media['file_id'],'file_unique_id':media['file_unique_id'],'mode':mode,'remote_bytes':media.get('file_size')}
                    self._save(receipt_file,ack)
                    break
                except DeliveryError as e:
                    last=e
                    if e.code in ['telegram_401','telegram_403','invalid_delivery_receipt']:break
            if message is None or mode is None:
                self._save(pending_file,{**job,'status':'failed','error_code':last.code})
                raise last
            # Separate remote readback checks that Telegram has the uploaded file.
            remote=self._retry('getFile',{'file_id':ack['file_id']})
            if remote['file_unique_id']!=ack['file_unique_id']:
                raise DeliveryError('remote_file_mismatch')
            if remote.get('file_size')!=ack['remote_bytes']:
                raise DeliveryError('remote_size_mismatch')
            receipt={**ack,'status':'confirmed','confirmed_at':time.time(),'remote_readback':True}
            self._save(receipt_file,receipt)
            pending_file.unlink(missing_ok=True)
            return receipt

    @staticmethod
    def _save(path,value):
        temporary=path.with_suffix(path.suffix+'.tmp')
        temporary.write_text(json.dumps(value,indent=2));temporary.chmod(0o600);temporary.replace(path)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('path',nargs='?');parser.add_argument('--chat',default=os.environ.get('TELEGRAM_CHAT_ID'))
    parser.add_argument('--caption',default='');parser.add_argument('--force',action='store_true');parser.add_argument('--health',action='store_true')
    args=parser.parse_args()
    try:
        client=TelegramDelivery()
        if not args.health and not args.chat: raise DeliveryError('missing_chat','Supply --chat or TELEGRAM_CHAT_ID')
        result=client.health() if args.health else client.send(args.path,args.chat,args.caption,args.force)
        print(json.dumps(result,indent=2))
    except Exception as e:
        # Do not emit stack traces or HTTP URLs with secrets.
        code=e.code if isinstance(e,DeliveryError) else type(e).__name__
        print(json.dumps({'ok':False,'error_code':code}));raise SystemExit(1)
