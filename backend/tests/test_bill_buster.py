from app import app

def test_bill_parse_and_analyze():
    c = app.test_client()
    # parse text
    r = c.post('/api/bill/parse', json={"text": "X-ray chest 340.00\nConsultation 120.00\nParacetamol 20.00"})
    assert r.status_code == 200
    j = r.get_json()
    assert j.get('status') == 'ok'
    items = j.get('parsed_items', [])
    assert len(items) >= 2

    # analyze
    r2 = c.post('/api/bill/analyze', json={"user_id":"U0001","parsed_items": items})
    assert r2.status_code == 200
    j2 = r2.get_json()
    assert j2.get('status') == 'ok'
    assert 'negotiation_snippet' in j2
    assert 'estimated_savings' in j2
