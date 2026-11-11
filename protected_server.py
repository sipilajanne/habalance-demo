"""Password-protected HaBalance demo; use behind HTTPS reverse proxy."""
import os, json, base64, hmac, time, threading, urllib.request, urllib.error
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from server import SYSTEM
ROOT = Path(__file__).resolve().parent
PASSWORD = os.environ.get('DEMO_PASSWORD','')
USERNAME = os.environ.get('DEMO_USER','habalance')
KEY = os.environ.get('OPENAI_API_KEY','')
PORT = int(os.environ.get('PORT','8000'))
if not PASSWORD or len(PASSWORD) < 12:
    raise SystemExit('Set DEMO_PASSWORD (at least 12 characters) before starting.')
RATE = {}
LOCK = threading.Lock()
class Handler(BaseHTTPRequestHandler):
    def headers_common(self, content_type='text/plain; charset=utf-8'):
        self.send_header('Content-Type',content_type)
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self' data: 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self' data:")
    def send_bytes(self,code,body,kind='text/plain; charset=utf-8',auth=False):
        self.send_response(code)
        self.headers_common(kind)
        if auth:self.send_header('WWW-Authenticate','Basic realm="HaBalance demo", charset="UTF-8"')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers();self.wfile.write(body)
    def authorized(self):
        auth=self.headers.get('Authorization','')
        try:
            scheme,token=auth.split(' ',1)
            if scheme.lower()!='basic':return False
            pair=base64.b64decode(token,validate=True).decode('utf-8')
            name,passw=pair.split(':',1)
            return hmac.compare_digest(name,USERNAME) and hmac.compare_digest(passw,PASSWORD)
        except (ValueError,UnicodeError):return False
    def guard(self):
        if not self.authorized():
            self.send_bytes(401,b'Kirjautuminen vaaditaan',auth=True);return False
        return True
    def do_GET(self):
        if not self.guard():return
        if self.path not in ('/','/index.html'):
            self.send_bytes(404,b'Not found');return
        self.send_bytes(200,(ROOT/'index.html').read_bytes(),'text/html; charset=utf-8')
    def do_POST(self):
        if not self.guard():return
        if self.path!='/api/chat':self.send_bytes(404,b'Not found');return
        if not KEY:self.send_bytes(503,b'AI not configured');return
        now=time.monotonic(); ip=self.client_address[0]
        with LOCK:
            hits=[x for x in RATE.get(ip,[]) if now-x<60]
            if len(hits)>=12:
                self.send_bytes(429,b'Too many requests');return
            hits.append(now);RATE[ip]=hits
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n<1 or n>12000:raise ValueError()
            data=json.loads(self.rfile.read(n))
            msgs=data.get('messages',[])
            if not isinstance(msgs,list):raise ValueError()
            clean=[{'role':m['role'],'content':m['content'][:2000]} for m in msgs[-12:] if isinstance(m,dict) and m.get('role') in ('user','assistant') and isinstance(m.get('content'),str)]
            if not clean or clean[-1]['role']!='user':raise ValueError()
            payload=json.dumps({'model':os.environ.get('OPENAI_MODEL','gpt-4.1-mini'),'messages':[{'role':'system','content':SYSTEM}]+clean,'max_tokens':350}).encode()
            req=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=payload,headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=25) as resp: answer=json.load(resp)['choices'][0]['message']['content']
            self.send_bytes(200,json.dumps({'reply':answer},ensure_ascii=False).encode(),'application/json; charset=utf-8')
        except (ValueError,KeyError,TypeError):self.send_bytes(400,b'Invalid request')
        except Exception:self.send_bytes(502,b'AI service unavailable')
if __name__=='__main__':
    print(f'HaBalance protected demo listening on port {PORT} (use HTTPS reverse proxy)')
    ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
