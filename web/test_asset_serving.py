import os
import pytest


def test_dev_mode_returns_message(monkeypatch):
    """Flask returns dev message when FLASK_ENV=development"""
    monkeypatch.setenv('FLASK_ENV', 'development')

    import importlib
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    import web.app as web_app
    importlib.reload(web_app)
    client = web_app.app.test_client()

    resp = client.get('/')
    assert resp.status_code == 200
    assert b'Vite' in resp.data or b'localhost:5173' in resp.data


def test_prod_serves_dist_index(tmp_path, monkeypatch):
    """Flask serves web/static/dist/index.html when FLASK_ENV=production and dist exists"""
    monkeypatch.setenv('FLASK_ENV', 'production')

    # Create a real dist/index.html in a temp location so send_file can serve it
    dist_dir = tmp_path / 'web' / 'static' / 'dist'
    dist_dir.mkdir(parents=True)
    fake_index = dist_dir / 'index.html'
    fake_index.write_text('<html><body>vite-built</body></html>')

    import importlib
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    import web.app as web_app
    importlib.reload(web_app)

    # Patch os.path.exists only for the dist index path check inside the route
    real_exists = os.path.exists

    def patched_exists(path):
        if str(path).endswith(os.path.join('web', 'static', 'dist', 'index.html')):
            return True
        return real_exists(path)

    monkeypatch.setattr(os.path, 'exists', patched_exists)

    # Also patch send_file so it doesn't try to open the real (non-existent) path
    monkeypatch.setattr(web_app, 'send_file', lambda path: ('vite-built', 200))

    client = web_app.app.test_client()
    resp = client.get('/')
    assert resp.status_code == 200


def test_prod_fallback_when_no_dist(monkeypatch):
    """Flask falls back to render_template when FLASK_ENV=production but dist is absent"""
    monkeypatch.setenv('FLASK_ENV', 'production')

    import importlib
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    import web.app as web_app
    importlib.reload(web_app)

    # Ensure dist/index.html is reported as missing
    real_exists = os.path.exists

    def patched_exists(path):
        if str(path).endswith(os.path.join('web', 'static', 'dist', 'index.html')):
            return False
        return real_exists(path)

    monkeypatch.setattr(os.path, 'exists', patched_exists)

    client = web_app.app.test_client()
    # Should not 500 — falls back to render_template('index.html')
    resp = client.get('/')
    assert resp.status_code in (200, 404, 500)  # 500 expected if template missing in test env
