from pathlib import Path
import base64,zipfile
p=Path('/mnt/data/habalance_demo')
s=(p/'index.html').read_text()
s=s.replace('Valmentajan esimerkkikeskustelu','HaBalancen läsnäoloassistentti')
s=s.replace('Demossa vastaukset ovat valmiiksi laadittuja, eivät tekoälyn tuottamia.','Demo käyttää esimerkkivastauksia ilman palvelinyhteyttä. Palvelimen kanssa käytössä on tekoälyvalmentaja. Älä jaa arkaluonteisia tietoja.')
s=s.replace('function send(ev){ev.preventDefault();', 'async function send(ev){ev.preventDefault();')
start=s.index("let a=/kiire|stress|työ/i.test(q)?")
end=s.index(";bubble(a,false)}",start)+len(';bubble(a,false)}')
s=s[:start]+'''const offline=/kiire|stress|työ/i.test(q)?'Kiire voi tuntua sekä mielessä että kehossa. Kokeile pysähtyä hetkeksi ja tuntea jalkapohjasi lattiaa vasten. Hengitä rauhallisesti kolme kertaa.':/väs|uni|palaut/i.test(q)?'Kuulostaa siltä, että pieni palautumishetki voisi tehdä hyvää. Anna itsellesi lupa levätä hetki ilman tavoitteita.':'Kiitos kun kerroit. Mitä huomaat kehossasi juuri nyt? Voit pysähtyä sen tuntemuksen äärelle hetkeksi.';
if(location.protocol==='file:'){bubble(offline,false);return;}
const pending=document.createElement('div');pending.className='bubble';pending.textContent='Hetkinen…';document.getElementById('messages').appendChild(pending);
try{const history=[...document.querySelectorAll('#messages .bubble')].filter(x=>x!==pending).slice(-12).map(x=>({role:x.classList.contains('user')?'user':'assistant',content:x.textContent}));const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:history})});if(!r.ok)throw Error('Palvelu ei vastaa');const data=await r.json();pending.textContent=data.reply||offline;}catch(e){pending.textContent=offline+' (Esimerkkivastaus: tekoälypalvelu ei ole käytössä.)';}}
''' + s[end:]
(p/'index.html').write_text(s)
Path('/mnt/data/HaBalance_demo.html').write_text(s)
(p/'server.py').write_text('''"""HaBalance demo backend. Run: OPENAI_API_KEY=... python server.py"""
import os, json, urllib.request, urllib.error
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
os.chdir(Path(__file__).resolve().parent)
SYSTEM = """Olet HaBalancen lämmin, rauhallinen suomenkielinen läsnäoloassistentti. Auta kiireisessä arjessa lyhyillä käytännön läsnäoloharjoituksilla. Vastaa enintään 100 sanalla. Älä esitä olevasi oikea ihminen tai HaBalancen valmentaja. Älä diagnosoi tai väitä korvaavasi terveydenhuoltoa. Jos käyttäjä kertoo välittömästä vaarasta tai itsetuhoisuudesta, ohjaa kiireelliseen apuun ja Suomessa numeroon 112."""
class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/api/chat': self.send_error(404); return
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n<1 or n>12000: self.send_error(413); return
            data=json.loads(self.rfile.read(n))
            msgs=data.get('messages',[])
            if not isinstance(msgs,list): raise ValueError('Invalid messages')
            clean=[{'role':m['role'],'content':str(m['content'])[:2000]} for m in msgs[-12:] if isinstance(m,dict) and m.get('role') in ('user','assistant') and isinstance(m.get('content'),str)]
            if not clean or clean[-1]['role']!='user': raise ValueError('Missing user message')
            key=os.environ.get('OPENAI_API_KEY')
            if not key: self.send_error(503,'OPENAI_API_KEY missing'); return
            payload=json.dumps({'model':os.environ.get('OPENAI_MODEL','gpt-4.1-mini'),'messages':[{'role':'system','content':SYSTEM}]+clean,'max_tokens':250}).encode()
            req=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=payload,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=25) as response: result=json.load(response)
            reply=result['choices'][0]['message']['content']
            raw=json.dumps({'reply':reply},ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        except (ValueError,KeyError,TypeError): self.send_error(400,'Invalid request')
        except (urllib.error.URLError,TimeoutError): self.send_error(502,'AI service unavailable')
if __name__=='__main__':
    print('HaBalance: http://localhost:8000')
    ThreadingHTTPServer(('127.0.0.1',8000),Handler).serve_forever()
''')
(p/'README.txt').write_text('HaBalance-demo\n\nAvaa index.html selaimessa: toimii offline-esimerkkivastauksilla.\n\nTekoälykeskustelu paikallisella palvelimella:\n1. Asenna Python 3.\n2. Aseta OPENAI_API_KEY ympäristömuuttujaksi omassa koneessasi (älä laita avainta HTML-tiedostoon).\n3. Aja python server.py tässä kansiossa.\n4. Avaa http://localhost:8000\n\nTämä on kehitysdemo, ei julkiseen internetiin turvallisesti julkaistava palvelu. Julkaisua varten tarvitaan käyttäjähallinta, tietosuojaseloste, kulurajat, väärinkäytön esto ja palvelininfra.\n',encoding='utf-8')
with zipfile.ZipFile('/mnt/data/HaBalance_demo.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in ['index.html','logo.jpg','valmentaja.jpg','server.py','README.txt']:z.write(p/name,'HaBalance/'+name)
print('OK',len(s))
