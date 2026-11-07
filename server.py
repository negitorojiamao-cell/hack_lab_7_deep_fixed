#!/usr/bin/env python3
"""HACK//LAB 7.0 DEEP local web server; stdlib only, Gemini API stays server-side."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import os, json, time, threading, datetime, mimetypes, html

BASE = Path(__file__).resolve().parent

def load_env(path):
    if not path.exists(): return
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        key, value = line.split('=', 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ: os.environ[key] = value

load_env(BASE / '.env')
API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
if API_KEY in ('貼り付けたGemini_APIキー', 'YOUR_API_KEY', 'your_api_key', 'changeme'): API_KEY = ''
MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite').strip()
PORT = int(os.getenv('HACKLAB_PORT', '8765'))
try: DAILY_LIMIT = max(1, min(20, int(os.getenv('HACKLAB_DAILY_AI_LIMIT', '20'))))
except ValueError: DAILY_LIMIT = 20
MIN_INTERVAL = 3.0
USAGE_FILE = BASE / '.hacklab_usage.json'
USAGE_LOCK = threading.Lock()
LAST_REQUEST_AT = 0.0

def _usage_read():
    today = datetime.date.today().isoformat()
    try:
        data = json.loads(USAGE_FILE.read_text(encoding='utf-8'))
        if data.get('date') != today: return {'date': today, 'count': 0}
        return {'date': today, 'count': int(data.get('count', 0))}
    except Exception:
        return {'date': today, 'count': 0}

def _usage_write(data):
    tmp = USAGE_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(data), encoding='utf-8')
    tmp.replace(USAGE_FILE)

def _usage_status():
    with USAGE_LOCK: d = _usage_read()
    return {'requests_today': d['count'], 'daily_limit': DAILY_LIMIT, 'remaining': max(0, DAILY_LIMIT-d['count'])}

SYSTEM_PROMPT = """あなたはHACK//LAB 7.0 DEEPの日本語システム学習家庭教師です。
相手は完全初心者かもしれないので、専門用語を導入したら短く定義し、前提を省略しないでください。
学習方針:
1. まず概念・目的・仕組みを具体例やたとえで説明し、いきなり完成回答を投げない。
2. teachは段階的な説明＋理解確認を1問、hintは答えを明かさない短いヒント、debugは症状/観測事実/仮説/小さな検証の順、reviewは誤解を丁寧に指摘、solutionは学習に必要な場合に限って解説例と理由を示す。
3. ユーザーの回答がある場合、正誤だけでなく理由を説明する。分からないと言われたら、もっと基礎に戻る。
4. Linuxではroot/sudoとネットワークrouteを区別する。コマンドは何をするか、引数、副作用、確認方法、戻し方を説明する。破壊的操作は避ける。
5. ネットワーク・セキュリティは自分の機器、許可された環境、隔離VM/CTFに限定する。第三者への無断侵入、認証回避、資格情報窃取、マルウェアや破壊活動の手順は提供せず、防御や安全なラボへ案内する。
6. 実在の秘密情報を求めない。キー、パスワード、トークンを貼るよう促さない。
7. 余計なあいさつより実際の学習支援を優先。日本語、具体的、根拠と限界を明示。
8. 不明なGoogle GeminiのモデルやAPIの状況を断言しない。""" 

class Handler(SimpleHTTPRequestHandler):
    server_version = 'HACKLAB/7.0'
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(BASE), **kwargs)
    def log_message(self, fmt, *args):
        # Keep local server logs useful without echoing request bodies or secrets.
        print('[%s] %s' % (self.log_date_time_string(), fmt % args))
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers(); self.wfile.write(body)
    def _read_json(self, max_bytes=40000):
        try: length = int(self.headers.get('Content-Length', '0'))
        except ValueError: length = 0
        if length < 1 or length > max_bytes: raise ValueError('リクエストサイズが不正です（最大40KB）。')
        return json.loads(self.rfile.read(length).decode('utf-8'))
    def do_GET(self):
        parsed = urlparse(self.path); route = unquote(parsed.path)
        if route == '/api/status':
            stat = _usage_status(); self._json(200, {'ai_configured': bool(API_KEY), **stat, 'provider': 'Google Gemini' if API_KEY else None, 'model': MODEL if API_KEY else None}); return
        # Never serve dotfiles, credentials, usage files, Python cache or raw private data.
        parts = Path(route.lstrip('/')).parts
        if any(p.startswith('.') for p in parts) or route in ('/data/course.json',):
            self.send_error(404); return
        if route == '/': self.path = '/index.html'
        else: self.path = route
        if any(p in ('__pycache__',) for p in parts): self.send_error(404); return
        return super().do_GET()
    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != '/api/teach': self._json(404, {'error': 'API endpoint not found'}); return
        if not API_KEY:
            self._json(503, {'error': 'Gemini APIキーが未設定です。.env に GEMINI_API_KEY を設定し、サーバーを再起動してください。キーはブラウザへ送らずサーバー内で保管します。'}); return
        try: payload = self._read_json()
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as e:
            self._json(400, {'error': str(e) or 'JSONを読み取れませんでした。'}); return
        question = str(payload.get('question', '')).strip()
        mode = str(payload.get('mode', 'teach'))[:20]
        context = payload.get('context', {})
        history = payload.get('history', [])
        if not question: self._json(400, {'error': '質問を入力してください。'}); return
        if len(question) > 5000: self._json(413, {'error': '質問が長すぎます。5000文字以内にしてください。'}); return
        if not isinstance(context, dict): context = {}
        # Whitelist fields so the frontend can only send a bounded learning context.
        safe_context = {}
        for k in ('app','lessonId','title','track','level','summary','core','concepts','commands','practice','quiz','safety','teaching','workflow','failure_modes','detailed'):
            v = context.get(k)
            if isinstance(v, (str,int,float,bool)): safe_context[k] = str(v)[:5200 if k == 'detailed' else 2400]
            elif isinstance(v, list): safe_context[k] = [str(x)[:160] for x in v[:12]]
        safe_history=[]
        if isinstance(history,list):
            for item in history[-6:]:
                if isinstance(item,dict): safe_history.append({'role':str(item.get('role',''))[:10], 'text':str(item.get('text',''))[:1000]})
        global LAST_REQUEST_AT
        with USAGE_LOCK:
            stat = _usage_read()
            if stat['count'] >= DAILY_LIMIT:
                self._json(429, {'error': f'アプリの本日利用上限（{DAILY_LIMIT}回）に達しました。明日リセットされます。別の有料モデルへの切替は行いません。'}); return
            now=time.monotonic()
            wait = MIN_INTERVAL - (now - LAST_REQUEST_AT)
            if wait > 0:
                self._json(429, {'error': f'送信間隔を空けてください。約{int(wait)+1}秒後にもう一度試してください。'}); return
            LAST_REQUEST_AT=now
            stat['count'] += 1
            try: _usage_write(stat)
            except Exception: pass
        mode_guidance = {
            'teach':'基礎からの説明。定義→比喩→具体例→小さな確認問題の順。いきなり答えを省略せず説明する。',
            'hint':'答えや完成コードを直接出さず、1〜3段階のヒントだけ。まず考える箇所を示す。',
            'debug':'まずエラー・期待値・実際の結果を整理し、観測できる事実と仮説を分け、最小の安全な検証を提案する。',
            'review':'ユーザーの理解や説明をレビューし、正確な部分・曖昧な部分・誤解・次の練習を具体的に返す。',
            'solution':'答え例を示してよいが、考え方、前提、各行の理由、安全性、代替案と理解確認を必ず添える。'
        }.get(mode, '概念から丁寧に説明し、最後に理解確認を1問出す。')
        prompt = '【学習モード】\n'+mode_guidance+'\n\n【現在の教材コンテキスト】\n'+json.dumps(safe_context,ensure_ascii=False)+'\n\n【直近の会話】\n'+json.dumps(safe_history,ensure_ascii=False)+'\n\n【学習者からの質問】\n'+question
        body = {
            'system_instruction': {'parts': [{'text': SYSTEM_PROMPT}]},
            'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
            'generationConfig': {'temperature': 0.45, 'maxOutputTokens': 1500}
        }
        url = 'https://generativelanguage.googleapis.com/v1beta/models/' + MODEL + ':generateContent'
        req = Request(url, data=json.dumps(body,ensure_ascii=False).encode('utf-8'), headers={'Content-Type':'application/json','x-goog-api-key':API_KEY}, method='POST')
        try:
            with urlopen(req, timeout=45) as response: raw=response.read(2_000_000)
            data=json.loads(raw.decode('utf-8'))
            candidates=data.get('candidates') or []
            texts=[]
            for c in candidates:
                for part in (c.get('content') or {}).get('parts',[]):
                    if isinstance(part,dict) and part.get('text'): texts.append(part['text'])
            answer='\n'.join(texts).strip()
            if not answer: self._json(502, {'error':'Geminiから回答が返りませんでした。モデル名やAI Studioでの利用状態を確認してください。'}); return
            self._json(200, {'answer':answer,'model':MODEL,'usage':_usage_status()})
        except HTTPError as e:
            raw=e.read(20000).decode('utf-8','replace')
            try:
                detail=json.loads(raw).get('error',{}).get('message','')
            except Exception: detail=''
            lower=(detail+' '+raw).lower()
            if e.code==429 or 'quota' in lower or 'resource_exhausted' in lower:
                msg='Geminiの無料枠またはレート制限に達した可能性があります。AI Studioの利用状況を確認し、時間をおいて再試行してください。有料モデルへの自動切替はしません。'
                self._json(429, {'error':msg,'provider_message':detail[:500]}); return
            if e.code in (400,404):
                msg='Gemini APIがリクエストまたはモデルを受け付けませんでした。GEMINI_MODELとGoogle AI Studioでのモデル利用可否を確認してください。'
            elif e.code in (401,403): msg='Gemini APIキーの認証・権限に問題があります。AI Studioでキーとプロジェクトを確認してください。'
            else: msg=f'Gemini APIエラー（HTTP {e.code}）。'
            self._json(e.code if 400<=e.code<600 else 502, {'error':msg,'provider_message':detail[:500]})
        except (URLError, TimeoutError) as e:
            self._json(502, {'error':'Gemini APIに接続できませんでした。ネット接続・タイムアウトを確認してください。','detail':str(e)[:300]})
        except Exception as e:
            self._json(500, {'error':'サーバー側で予期しない問題が起きました。','detail':str(e)[:300]})

if __name__ == '__main__':
    if not (BASE / 'index.html').exists(): raise SystemExit('index.html not found')
    print('HACK//LAB 7.0 DEEP')
    print(f'Open: http://127.0.0.1:{PORT}/')
    print('Provider: Google Gemini API; key remains server-side.')
    print(f'AI daily app cap: {DAILY_LIMIT}; minimum interval: {MIN_INTERVAL}s; no model fallback.')
    if not API_KEY: print('Gemini key not configured. Edit .env (copy .env.example) to enable tutor.')
    try: ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
    except KeyboardInterrupt: print('\nServer stopped.')
