"""Local-only coding duel prototype. No saves, accounts or multiplayer."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import rooms

ROOT = Path(__file__).resolve().parents[2]
CHECKS = {
    ('potion', 0): 'assert can_buy(10, 4) is True\nassert can_buy(4, 4) is True\nassert can_buy(3, 4) is False',
    ('potion', 1): 'assert buy_potion(10, 4) == 6\nassert buy_potion(4, 4) == 0\nassert buy_potion(3, 4) == 3',
    ('potion', 2): 'assert buy_potion(10, -4) == 10\nassert buy_potion(10, 4) == 6\nassert buy_potion(3, 4) == 3',
    ('chest', 0): 'assert chest_reward(10, 5) == 15\nassert chest_reward(0, 0) == 0\nassert chest_reward(100, 2) == 102',
    ('chest', 1): 'assert chest_reward(10, 5, False) == 10\nassert chest_reward(10, 5, True) == 15\nassert chest_reward(0, 3, True) == 3',
    ('chest', 2): 'assert collect_chests(10, [(5, True), (7, False), (3, True)]) == 18\nassert collect_chests(4, []) == 4\nassert collect_chests(0, [(7, False)]) == 0',
}
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)
    def do_POST(self):
        if self.path not in ('/check', '/run') and not self.path.startswith('/room/'):
            self.send_error(404); return
        if self.headers.get('Origin') != 'http://127.0.0.1:8901' or self.headers.get_content_type() != 'application/json':
            self.send_error(403); return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 30000: raise ValueError('Invalid request size')
            data = json.loads(self.rfile.read(size))
            if self.path.startswith('/room/'):
                try:
                    result = rooms.handle(self.path.removeprefix('/room/'), data)
                    body = json.dumps(result).encode()
                    self.send_response(200)
                except ValueError as exc:
                    body = json.dumps({'error': str(exc)}).encode()
                    self.send_response(400)
                self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
                return
            if self.path == '/run':
                code = data['code']
                stdin = data.get('stdin', '')
                if not isinstance(code, str) or len(code) > 20000 or not isinstance(stdin, str) or len(stdin) > 4000:
                    raise ValueError('Invalid code or input')
                with tempfile.TemporaryDirectory(prefix='questlab-duel-run-') as folder:
                    script = Path(folder) / 'answer.py'
                    script.write_text(code, encoding='utf-8')
                    try:
                        done = subprocess.run([sys.executable, '-I', '-S', str(script)], cwd=folder,
                            input=stdin, capture_output=True, timeout=3, text=True)
                        output = (done.stdout + done.stderr)[-6000:] or '(No output. Add print(...) to see a result.)'
                        result = {'output': output, 'exit_code': done.returncode}
                    except subprocess.TimeoutExpired:
                        result = {'output': 'Stopped after 3 seconds. Check for a loop or missing input.', 'exit_code': None}
                body = json.dumps(result).encode()
                self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
                return
            chain, step, code = data['chain'], int(data['step']), data['code']
            check = CHECKS[(chain, step)]
            if not isinstance(code, str) or len(code) > 20000: raise ValueError('Invalid code')
            with tempfile.TemporaryDirectory(prefix='questlab-duel-') as folder:
                script = Path(folder) / 'answer.py'
                script.write_text(code + '\n\n' + check + '\n', encoding='utf-8')
                try:
                    done = subprocess.run([sys.executable, '-I', '-S', str(script)], cwd=folder,
                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                        timeout=3, text=True)
                    passed = done.returncode == 0
                    feedback = 'All checks passed.' if passed else 'A check failed or your code raised an error. Review your function and try again next step.'
                except subprocess.TimeoutExpired:
                    passed, feedback = False, 'Your code took too long. Check for an infinite loop.'
            body = json.dumps({'passed': passed, 'feedback': feedback}).encode()
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            self.send_error(400, 'Invalid duel submission')

if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', 8901), Handler)
    print('Local duel: http://127.0.0.1:8901/prototypes/duel-local/  (Ctrl+C to stop)', flush=True)
    server.serve_forever()
