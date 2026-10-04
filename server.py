from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import json
import os
import threading
import time
import urllib.parse
from sources import SOURCES, JST, fetch_city, minutes
from planner import plan_results

BASE = Path(__file__).resolve().parent / 'public'
SEARCH_LIMIT = threading.BoundedSemaphore(2)
CITY_LIMITS = {key: threading.BoundedSemaphore(1) for key in SOURCES}
FILES = {'/': ('index.html', 'text/html; charset=utf-8'),
         '/index.html': ('index.html', 'text/html; charset=utf-8'),
         '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
         '/styles.css': ('styles.css', 'text/css; charset=utf-8'),
         '/favicon.svg': ('favicon.svg', 'image/svg+xml')}


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def send(self, status, body, mime='application/json; charset=utf-8'):
        if isinstance(body, dict):
            body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store' if mime.startswith('application/json') else 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == '/health':
            self.send(200, {'ok': True})
        elif path in FILES:
            name, mime = FILES[path]
            self.send(200, (BASE / name).read_bytes(), mime)
        else:
            self.send(404, {'error': 'ページが見つかりません'})

    def do_POST(self):
        if self.path != '/api/search':
            self.send(404, {'error': 'ページが見つかりません'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 1024:
                raise ValueError('入力内容を確認してください')
            data = json.loads(self.rfile.read(length).decode('utf-8'))
            target = date.fromisoformat(data['date'])
            today = datetime.now(JST).date()
            if not today <= target <= today + timedelta(days=120):
                raise ValueError('今日から120日先までの日付を指定してください')
            start, end = minutes(data['start']), minutes(data['end'])
            if not 0 <= start < end <= 24 * 60:
                raise ValueError('終了時刻は開始時刻より後にしてください')
            cities = data.get('cities', list(SOURCES))
            if not isinstance(cities, list) or not cities or any(c not in SOURCES for c in cities):
                raise ValueError('検索する市を選択してください')
            cities = list(dict.fromkeys(cities))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            self.send(400, {'error': '日付・時刻・検索する市を確認してください。日付は今日から120日先まで指定できます。'})
            return
        if not SEARCH_LIMIT.acquire(blocking=False):
            self.send(429, {'error': '他の検索を処理しています。少し待ってからお試しください。'})
            return
        try:
            # SSE delivers each city as it finishes; one slow source does not hide others.
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store')
            self.send_header('Connection', 'close')
            self.send_header('X-Accel-Buffering', 'no')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.close_connection = True

            def emit(event, payload):
                message = f'event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n'
                self.wfile.write(message.encode('utf-8'))
                self.wfile.flush()

            def fetch_limited(city):
                if not CITY_LIMITS[city].acquire(timeout=1):
                    return {'id': city, 'name': SOURCES[city][0], 'status': 'error',
                            'courts': [], 'errors': ['この市を照会中です。しばらく待って再検索してください。'],
                            'checkedAt': datetime.now(JST).isoformat(timespec='seconds')}
                try:
                    return fetch_city(city, target)
                finally:
                    CITY_LIMITS[city].release()

            results = []
            emit('started', {'cities': cities})
            with ThreadPoolExecutor(max_workers=3) as pool:
                jobs = [pool.submit(fetch_limited, c) for c in cities]
                for job in as_completed(jobs):
                    result = job.result()
                    results.append(result)
                    emit('city', {'source': {k: v for k, v in result.items() if k != 'courts'},
                                  'courtCount': len(result['courts']),
                                  'plans': plan_results(results, start, end)})
            emit('done', {'plans': plan_results(results, start, end),
                          'checkedAt': datetime.now(JST).isoformat(timespec='seconds')})
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            SEARCH_LIMIT.release()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8765'))
    host = os.environ.get('HOST', '127.0.0.1')
    print(f'Tennis Court Finder: http://{host}:{port}', flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
