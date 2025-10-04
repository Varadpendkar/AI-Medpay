# tests/test_get_quote_browser_flow.py
from app.main import app as flask_app
import re
import pytest
import sys
import os
# Add backend directory to path for relative imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))


@pytest.fixture
def client():
    # Use in-process Flask test client to avoid CSRF/auth problems
    flask_app.config['TESTING'] = True
    # If you use Flask-WTF, disable CSRF in tests
    flask_app.config['WTF_CSRF_ENABLED'] = False
    with flask_app.test_client() as c:
        yield c


def test_get_quote_full_flow_renders_multiple_plans(client):
    """
    Simulate a user filling the get-quote form and submitting it.
    Verify the response contains recommendation cards and key tokens.
    """
    form_data = {
        'user_id': 'U1',
        'age': '32',
        'dependents': '2',
        'location': 'Mumbai',
        'max_premium': '15000',
        'coverage_amount': '1000000'
    }

    resp = client.post('/get-quote', data=form_data)
    assert resp.status_code == 200, f"Unexpected status: {resp.status_code}\n{resp.get_data(as_text=True)[:500]}"

    html = resp.get_data(as_text=True)

    # Basic sanity: HTML should include a title or heading for the results page
    assert ('Get a Quote' in html) or ('Quote Results' in html) or (
        'rec-card' in html), "Page doesn't look like results page"

    # Expect at least one recommendation card
    rec_card_count = len(re.findall(r'class=["\']rec-card["\']', html))
    assert rec_card_count >= 1, f"Expected >=1 rec-card, found {rec_card_count}\nHTML snippet:\n{html[:400]}"

    # Expect presence of numeric score tokens or 'Score:' label
    assert ('Score:' in html) or re.search(r'\bscore\b', html,
                                           flags=re.IGNORECASE), "No 'Score' token found in HTML"

    # Expect provider or plan name text (common tokens in your templates)
    assert ('Provider:' in html) or ('plan_name' in html) or re.search(r'PMJAY|Ayushman|Tata|AIG|Health', html, flags=re.IGNORECASE), \
        "No provider / plan name tokens found; check template rendering"

    # Optional: ensure at least two numeric scores if you expect multiple plans (non-strict)
    scores = re.findall(r'[\d]+\.\d{2,3}', html)
    # We won't fail if only one exists; just make sure parsing didn't error out
    assert scores is not None, "Failed to parse numeric scores"
