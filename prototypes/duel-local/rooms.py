"""In-memory, localhost-only duel rooms for the prototype. Not an online service."""
import secrets
import threading
import time

_lock = threading.RLock()
_rooms = {}


def _view(room, token):
    player = next((p for p in room['players'] if p['token'] == token), None)
    if not player:
        raise ValueError('Invalid room credential')
    other = next((p for p in room['players'] if p is not player), None)
    return {'code': room['code'], 'chain': room['chain'], 'step': room['step'],
            'phase': room['phase'], 'you': {'name': player['name'], 'hp': player['hp'],
            'submitted': player['submitted'], 'ready': player['ready'], 'focus': player['focus']},
            'opponent': None if other is None else {'name': other['name'], 'hp': other['hp'],
            'submitted': other['submitted'], 'ready': other['ready']},
            'result': room['results'].get(token), 'revision': room['revision']}


def _player(name):
    name = str(name).strip()[:24]
    if not name:
        raise ValueError('Enter a hunter name')
    return {'name': name, 'token': secrets.token_urlsafe(24), 'hp': 100, 'focus': 0,
            'submitted': False, 'ready': False, 'passed': False, 'stance': 'attack'}


def handle(action, data):
    with _lock:
        now = time.monotonic()
        for key in list(_rooms):
            if now - _rooms[key]['updated'] > 7200:
                del _rooms[key]
        if action == 'create':
            chain = data.get('chain')
            if chain not in ('potion', 'chest'):
                raise ValueError('Unknown challenge chain')
            host = _player(data.get('name', ''))
            while True:
                code = secrets.token_hex(3).upper()
                if code not in _rooms: break
            room = {'code': code, 'chain': chain, 'players': [host], 'step': 0,
                    'phase': 'waiting', 'results': {}, 'revision': 0, 'updated': now}
            _rooms[code] = room
            return {'token': host['token'], 'room': _view(room, host['token'])}
        code = str(data.get('code', '')).strip().upper()
        room = _rooms.get(code)
        if room is None: raise ValueError('Room not found')
        room['updated'] = now
        if action == 'join':
            if len(room['players']) != 1 or room['phase'] != 'waiting':
                raise ValueError('Room is full')
            player = _player(data.get('name', ''))
            room['players'].append(player)
            room['phase'] = 'playing'
            room['revision'] += 1
            return {'token': player['token'], 'room': _view(room, player['token'])}
        token = data.get('token', '')
        _view(room, token)
        player = next(p for p in room['players'] if p['token'] == token)
        if action == 'state':
            return {'room': _view(room, token)}
        if action == 'submit':
            if room['phase'] != 'playing' or player['submitted'] or data.get('step') != room['step']:
                raise ValueError('This round is not accepting your answer')
            if not isinstance(data.get('passed'), bool) or data.get('stance') not in ('attack', 'guard', 'focus'):
                raise ValueError('Invalid result')
            player.update(submitted=True, passed=data['passed'], stance=data['stance'])
            if all(p['submitted'] for p in room['players']):
                a, b = room['players']
                damage = {}
                for p, opponent in ((a, b), (b, a)):
                    dealt = (20 if opponent['passed'] else 30) if p['passed'] else 0
                    if p['passed']:
                        dealt += p['focus']
                        p['focus'] = 0
                        if p['stance'] == 'attack': dealt += 10
                        if p['stance'] == 'focus': p['focus'] = 10
                    if opponent['stance'] == 'guard': dealt = max(0, dealt - 10)
                    damage[p['token']] = dealt
                a['hp'] = max(0, a['hp'] - damage[b['token']])
                b['hp'] = max(0, b['hp'] - damage[a['token']])
                room['results'] = {p['token']: {'passed': p['passed'], 'opponent_passed': o['passed'],
                    'dealt': damage[p['token']], 'taken': damage[o['token']]}
                    for p, o in ((a, b), (b, a))}
                room['phase'] = 'finished' if room['step'] == 2 or a['hp'] == 0 or b['hp'] == 0 else 'result'
            room['revision'] += 1
            return {'room': _view(room, token)}
        if action == 'ready':
            if room['phase'] != 'result' or data.get('step') != room['step']:
                raise ValueError('Not ready for the next challenge')
            player['ready'] = True
            if all(p['ready'] for p in room['players']):
                room['step'] += 1
                room['phase'] = 'playing'
                room['results'] = {}
                for p in room['players']:
                    p['ready'] = p['submitted'] = False
            room['revision'] += 1
            return {'room': _view(room, token)}
        raise ValueError('Unknown room action')
