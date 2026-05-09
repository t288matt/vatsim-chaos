"""
Tests for Task 5.1: Verify that all Flask API endpoints return the standard
{ok: true, data: ...} or {ok: false, error: ...} response envelope.

Run from the repository root:
    pytest web/test_api_responses.py -v
"""

import sys
import os
import json
import pytest

# Ensure the web/ package is on the path so `from app import app` resolves
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def client_no_briefing(client):
    """Test client with briefing file temporarily removed."""
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    briefing_path = os.path.join(parent_dir, 'pilot_briefing.txt')
    briefing_exists = os.path.exists(briefing_path)
    briefing_backup = None

    try:
        if briefing_exists:
            import shutil
            briefing_backup = briefing_path + '.backup'
            shutil.move(briefing_path, briefing_backup)
        yield client
    finally:
        if briefing_backup and os.path.exists(briefing_backup):
            import shutil
            shutil.move(briefing_backup, briefing_path)


# ---------------------------------------------------------------------------
# POST /upload
# ---------------------------------------------------------------------------

def test_upload_no_files_returns_error_envelope(client):
    """POST /upload with no files should return ok=false with an error field."""
    resp = client.post('/upload')
    body = json.loads(resp.data)
    assert resp.status_code == 400
    assert 'ok' in body
    assert body['ok'] is False
    assert 'error' in body
    assert isinstance(body['error'], str)


def test_upload_no_files_has_no_data_field(client):
    """Error responses must not include a data field."""
    resp = client.post('/upload')
    body = json.loads(resp.data)
    assert 'data' not in body


# ---------------------------------------------------------------------------
# GET /validate/<filename>
# ---------------------------------------------------------------------------

def test_validate_nonexistent_file_returns_error_envelope(client):
    """GET /validate/nonexistent.xml should return ok=false with an error field."""
    resp = client.get('/validate/nonexistent.xml')
    body = json.loads(resp.data)
    assert resp.status_code in (400, 404)
    assert 'ok' in body
    assert body['ok'] is False
    assert 'error' in body
    assert isinstance(body['error'], str)


# ---------------------------------------------------------------------------
# GET /files
# ---------------------------------------------------------------------------

def test_list_files_returns_ok_envelope(client):
    """GET /files should return ok=true with data as a list."""
    resp = client.get('/files')
    body = json.loads(resp.data)
    assert resp.status_code == 200
    assert 'ok' in body
    assert body['ok'] is True
    assert 'data' in body
    assert isinstance(body['data'], list)


def test_list_files_has_no_error_field(client):
    """Successful responses must not include an error field."""
    resp = client.get('/files')
    body = json.loads(resp.data)
    assert 'error' not in body


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------

def test_get_status_returns_ok_envelope(client):
    """GET /status should return ok=true with data containing is_processing."""
    resp = client.get('/status')
    body = json.loads(resp.data)
    assert resp.status_code == 200
    assert 'ok' in body
    assert body['ok'] is True
    assert 'data' in body
    assert 'is_processing' in body['data']


# ---------------------------------------------------------------------------
# POST /process
# ---------------------------------------------------------------------------

def test_process_no_files_returns_error_envelope(client):
    """POST /process with no files selected should return ok=false."""
    resp = client.post(
        '/process',
        data=json.dumps({'files': []}),
        content_type='application/json'
    )
    body = json.loads(resp.data)
    assert resp.status_code == 400
    assert 'ok' in body
    assert body['ok'] is False
    assert 'error' in body
    assert isinstance(body['error'], str)


def test_process_empty_files_list_returns_error_envelope(client):
    """POST /process with an empty files list should return ok=false."""
    resp = client.post(
        '/process',
        data=json.dumps({}),
        content_type='application/json'
    )
    body = json.loads(resp.data)
    assert 'ok' in body
    assert body['ok'] is False
    assert 'error' in body


# ---------------------------------------------------------------------------
# DELETE /delete-file/<filename>
# ---------------------------------------------------------------------------

def test_delete_nonexistent_file_returns_error_envelope(client):
    """DELETE /delete-file/nonexistent.xml should return ok=false."""
    resp = client.delete('/delete-file/nonexistent.xml')
    body = json.loads(resp.data)
    assert resp.status_code in (400, 404)
    assert 'ok' in body
    assert body['ok'] is False
    assert 'error' in body
    assert isinstance(body['error'], str)


# ---------------------------------------------------------------------------
# POST /validate-same-routes
# ---------------------------------------------------------------------------

def test_validate_same_routes_no_files_returns_error_envelope(client):
    """POST /validate-same-routes with no files should return ok=false."""
    resp = client.post(
        '/validate-same-routes',
        data=json.dumps({'files': []}),
        content_type='application/json'
    )
    body = json.loads(resp.data)
    assert resp.status_code == 400
    assert 'ok' in body
    assert body['ok'] is False
    assert 'error' in body


# ---------------------------------------------------------------------------
# GET /briefing — error path (file will not exist in test env)
# ---------------------------------------------------------------------------

def test_briefing_not_found_returns_error_envelope(client_no_briefing):
    """GET /briefing when no briefing file exists should return ok=false."""
    resp = client_no_briefing.get('/briefing')
    body = json.loads(resp.data)
    assert resp.status_code == 404
    assert 'ok' in body
    assert body['ok'] is False
    assert 'error' in body
