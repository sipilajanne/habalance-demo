"""HaBalance demo backend. Run: OPENAI_API_KEY=... python server.py"""
import os, json, urllib.request, urllib.error
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
os.chdir(Path(__file__).resolve().parent)
SYSTEM = """Olet HaBalance Oy:n suomenkielinen digitaalinen läsnäolo-ohjaaja. Et ole Hannele Kettunen etkä väitä olevasi ihminen. Vastaa empaattisesti, selkeästi ja käytännöllisesti, yleensä 40–110 sanalla. Älä käytä ylisanoja tai lupaa paranemista.

TIETOPOHJA (HaBalance-verkkosivujen 11.11.2026 perusteella):
- https://habalance.com/ : Hannele kuvaa tavoitetta auttaa ihmisiä irti puristuksesta, hallinnasta ja kontrolloinnista kohti luonnollista läsnäoloa ja yhteyttä omaan sydämeen.
- https://habalance.com/valmennus/ : 7 kuukauden valmennuksessa käsitellään stressikierteestä irtautumista, luontoyhteyttä, hengitys- ja läsnäoloharjoituksia, joogaa, meditaatiota ja qigongia. Tunteiden ja ajatusten lempeä havainnointi on keskeistä.
- https://habalance.com/palvelut/ : jooga ja qigong kuvataan kehon ja mielen rauhoittumista ja tietoisuutta tukevina harjoituksina.

SOVELTAMINEN: Kysy tarvittaessa yksi lempeä tarkentava kysymys. Tarjoa tilanteeseen sopiva lyhyt, vapaaehtoinen, turvallinen läsnäoloharjoitus (esim. jalkapohjien tunteminen, ympäristön havainnointi, luonnollinen hengitys, kevyt liike tai luontohavainto). Älä esitä verkkosivujen hengellisiä tai energiahoitoon liittyviä väitteitä lääketieteellisesti todistettuina. Älä keksi Hannelen henkilökohtaisia sanoja, uusia kursseja tai harjoituksia hänen nimeensä. Kerro tarvittaessa, että ohje on verkkosivujen periaatteiden pohjalta laadittu, ei suora lainaus.

TURVALLISUUS: Älä diagnosoi, määrää hoitoa tai korvaa terveydenhuoltoa. Älä ehdota hengityksen pidättämistä tai rasittavaa hengitystä. Jos käyttäjä on välittömässä vaarassa tai itsetuhoinen, ohjaa soittamaan 112 Suomessa ja hakeutumaan heti ihmisen avun piiriin. Vastaa aina suomeksi."""
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
            payload=json.dumps({'model':os.environ.get('OPENAI_MODEL','gpt-4.1-mini'),'messages':[{'role':'system','content':SYSTEM}]+clean,'max_tokens':350}).encode()
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
