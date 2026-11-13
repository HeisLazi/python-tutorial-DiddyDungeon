from pathlib import Path

from fastapi.testclient import TestClient

from ide.server import app_v2


def test_external_change_blocks_save_and_format_until_reconciled(tmp_path, monkeypatch):
    monkeypatch.setattr(app_v2, 'WORKSPACE', tmp_path)
    target = tmp_path / 'quest.py'
    target.write_text('print("original")\n')
    client = TestClient(app_v2.app, base_url='http://127.0.0.1')
    initial = client.get('/api/file', params={'path': 'quest.py'}).json()
    target.write_text('print("external")\n')
    for endpoint, method in [('/api/file', client.put), ('/api/format', client.post)]:
        response = method(endpoint, json={'path': 'quest.py', 'content': 'print("game")\n', 'expected_revision': initial['revision']})
        assert response.status_code == 409
        assert target.read_text() == 'print("external")\n'
    external = client.get('/api/file', params={'path': 'quest.py'}).json()
    saved = client.put('/api/file', json={'path': 'quest.py', 'content': 'print("game")\n', 'expected_revision': external['revision']})
    assert saved.status_code == 200
    assert target.read_text() == 'print("game")\n'
    assert saved.json()['revision'] != initial['revision']


def test_deleted_file_requires_explicit_recreate(tmp_path, monkeypatch):
    monkeypatch.setattr(app_v2, 'WORKSPACE', tmp_path)
    target = tmp_path / 'quest.py'
    target.write_text('original')
    client = TestClient(app_v2.app, base_url='http://127.0.0.1')
    revision = client.get('/api/file', params={'path': 'quest.py'}).json()['revision']
    target.unlink()
    assert client.put('/api/file', json={'path': 'quest.py', 'content': 'recreated', 'expected_revision': revision}).status_code == 409
    assert not target.exists()
    assert client.put('/api/file', json={'path': 'quest.py', 'content': 'recreated', 'expected_revision': 'missing'}).status_code == 200
    assert target.read_text() == 'recreated'
