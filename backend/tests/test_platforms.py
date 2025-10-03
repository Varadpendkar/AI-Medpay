from app import app

def test_platform_endpoints():
    c = app.test_client()
    rp = c.get('/api/platforms')
    assert rp.status_code == 200
    plats = rp.get_json().get('platforms', [])
    assert any(p.get('id') == 'internal' for p in plats)

    rint = c.get('/api/platforms/plans?source=internal&limit=5')
    assert rint.status_code == 200
    plans = rint.get_json().get('plans', [])
    if plans:
        pid = plans[0].get('plan_id')
        rd = c.get(f'/api/plan/{pid}')
        assert rd.status_code == 200
        assert 'plan' in rd.get_json()
