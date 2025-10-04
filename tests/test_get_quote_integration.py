"""Test get-quote endpoint integration."""
from backend.app.main import app


def test_get_quote_endpoint():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as c:
        resp = c.post(
            '/get-quote', data={'user_id': 'U1', 'age': '32', 'location': 'Mumbai'})
        assert resp.status_code == 200
        content = resp.get_data(as_text=True)
        assert 'recommendations' in content or 'Plan' in content or 'rec-card' in content
