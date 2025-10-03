import json
import pytest
from backend.app.main import app


def test_recommendations_schema():
    c = app.test_client()
    r = c.get('/api/recommendations?user_id=U0001&limit=3')
    assert r.status_code == 200
    j = r.get_json()
    assert 'recommendations' in j
    recs = j['recommendations']
    assert isinstance(recs, list)
    assert len(recs) <= 3
    if recs:
        r0 = recs[0]
        # canonical fields
        for key in ['plan_id', 'provider', 'plan_name', 'monthly_premium', 'deductible', 'network_size', 'score', 'rank']:
            assert key in r0
        # explainability
        assert 'explain_text' in r0
        assert 'explain_scores' in r0
        assert isinstance(r0['explain_scores'], dict)
        # explain_top_features is optional but preferred
        assert 'explain_top_features' in r0
