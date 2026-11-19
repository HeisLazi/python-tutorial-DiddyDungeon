"""Quest Lab connection lobby; Python 3.10+, no third-party packages.

This service handles lobby presence only. It has no code execution or save access.
Serve behind HTTPS for remote use; the default bind is loopback.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import argparse
import hmac
import json
import secrets
import threading
import time

ROOT = Path(__file__).resolve().parent
LOCK = threading.RLock()
ROOMS = {}
TTL = 60 * 60
HEARTBEAT = 30
MAX_ROOMS = 256


def player(name):
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 24:
        raise ValueError('Enter a hunter name of 1–24 characters.')
    return {'name': name.strip(), 'token': secrets.token_urlsafe(32), 'ready': False, 'last_seen': time.monotonic()}


def room_view(room, member):
    now = time.monotonic()
    return {'room': room['id'], 'members': [{'name': p['name'], 'ready': p['ready'],
            'online': now - p['last_seen'] <= HEARTBEAT, 'you': p is member} for p in room['players']],
            'both_ready': len(room['players']) == 2 and all(p['ready'] and now - p['last_seen'] <= HEARTBEAT for p in room['players'])}


def dispatch(action, data):
    with LOCK:
        now = time.monotonic()
        for key in list(ROOMS):
            if now - ROOMS[key]['last_activity'] > TTL:
                del ROOMS[key]
        if action == 'create':
            if len(ROOMS) >= MAX_ROOMS: raise ValueError('The lobby is full. Try again later.')
            host = player(data.get('name'))
            key = secrets.token_urlsafe(18)
            room = {'id': key, 'players': [host], 'last_activity': now}
            ROOMS[key] = room
            return {'token': host['token'], 'state': room_view(room, host)}
        key = data.get('room')
        if not isinstance(key, str) or len(key) > 128: raise ValueError('Invalid room invitation.')
        room = ROOMS.get(key)
        if not room: raise ValueError('Room not found or expired.')
        if action == 'join':
            if len(room['players']) >= 2: raise ValueError('This room already has two hunters.')
            member = player(data.get('name'))
            room['players'].append(member)
            room['last_activity'] = now
            return {'token': member['token'], 'state': room_view(room, member)}
        token = data.get('token')
        if not isinstance(token, str) or len(token) > 128: raise ValueError('Invalid room membership.')
        member = next((p for p in room['players'] if hmac.compare_digest(p['token'], token)), None)
        if not member: raise ValueError('Invalid room membership.')
        member['last_seen'] = now
        room['last_activity'] = now
        if action == 'ready':
            if not isinstance(data.get('ready'), bool): raise ValueError('Invalid ready status.')
            member['ready'] = data['ready']
        elif action == 'leave':
            room['players'].remove(member)
            for p in room['players']: p['ready'] = False
            if not room['players']: del ROOMS[key]
            return {'left': True}
        elif action != 'state':
            raise ValueError('Unknown action.')
        return {'state': room_view(room, member)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Room invitation tokens are secrets: never log request URLs.
        pass

    def _send(self, status, body, content_type='application/json; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlsplit(self.path).path != '/':
            self._send(404, b'Not found', 'text/plain; charset=utf-8'); return
        self._send(200, (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')

    def do_POST(self):
        action = urlsplit(self.path).path.removeprefix('/api/')
        if urlsplit(self.path).path != '/api/' + action or action not in ('create', 'join', 'state', 'ready', 'leave'):
            self._send(404, b'{}'); return
        if self.headers.get_content_type() != 'application/json':
            self._send(415, b'{}'); return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > 2048: raise ValueError('Invalid request size.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict): raise ValueError('Invalid request.')
            result = dispatch(action, data)
            self._send(200, json.dumps(result).encode())
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._send(400, json.dumps({'error': str(exc)}).encode())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Quest Lab connection-only lobby')
    parser.add_argument('--host', default='127.0.0.1', help='Bind address; default is local only')
    parser.add_argument('--port', default=8902, type=int)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f'Quest Lab lobby listening on {args.host}:{args.port} (Ctrl+C to stop)', flush=True)
    server.serve_forever()
