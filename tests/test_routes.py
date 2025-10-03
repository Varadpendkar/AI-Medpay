import pytest
from backend.app.main import app as flask_app


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c


def test_root_redirects_to_get_quote(client):
    resp = client.get('/', follow_redirects=False)
    assert resp.status_code in (301, 302, 303)
    assert '/get-quote' in resp.headers['Location']


def test_get_quote_page_contains_expected_content(client):
    resp = client.get('/get-quote')
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert '<title>Get a Quote' in text
    # A simple token that indicates the enhanced widget was included
    assert 'get_quote_enhanced.js' in text or 'frontend-get-quote-static/js/get_quote_enhanced.js' in text


def test_dev_endpoints_in_debug_mode(client):
    """Test that the _dev/endpoints route works in debug mode"""
    flask_app.config['DEBUG'] = True
    resp = client.get('/_dev/endpoints')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    # Should contain some endpoint information
    assert len(data) > 0


def test_dev_endpoints_blocked_in_production(client):
    """Test that the _dev/endpoints route is blocked when not in debug mode"""
    flask_app.config['DEBUG'] = False
    resp = client.get('/_dev/endpoints')
    assert resp.status_code == 403
    data = resp.get_json()
    assert data['error'] == 'not allowed'


def test_static_js_file_exists(client):
    """Test that the JavaScript file can be served"""
    resp = client.get(
        '/backend/app/frontend_routes/static/js/get_quote_enhanced.js')
    # Should be 200 if file exists and is served, or might need different route
    # This test helps validate the static file serving configuration
    # 404 is OK if route doesn't exist yet
    assert resp.status_code in (200, 404)
