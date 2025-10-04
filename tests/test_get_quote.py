import pytest
from unittest.mock import patch, MagicMock
from backend.app.main import app as flask_app


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    # disable CSRF for tests if using Flask-WTF
    flask_app.config['WTF_CSRF_ENABLED'] = False
    with flask_app.test_client() as c:
        yield c


def test_get_quote_calls_model_success(client):
    """Test that the get-quote form successfully calls the recommendation model"""
    fake_recommendations = [
        {
            "plan_name": "Test Plan A",
            "provider": "Test Insurance Co",
            "price": "₹5,000/month",
            "coverage": "₹5 Lakh",
            "rating": 4.5,
            "confidence": 92,
            "plan_id": "test_plan_a",
            "deductible": 0,
            "network_size": 15000,
            "explain_text": "Excellent match based on your age and requirements",
            "rank": 1
        },
        {
            "plan_name": "Test Plan B",
            "provider": "Another Insurance Co",
            "price": "₹6,500/month",
            "coverage": "₹10 Lakh",
            "rating": 4.2,
            "confidence": 88,
            "plan_id": "test_plan_b",
            "deductible": 5000,
            "network_size": 12000,
            "explain_text": "Good coverage with reasonable premium",
            "rank": 2
        }
    ]

    # Mock the recommend_plans function
    with patch('backend.app.services.recommender.recommend_plans', return_value=fake_recommendations) as mock_rec:
        # Submit form data
        form_data = {
            'full-name': 'John Doe',
            'age': '35',
            'email': 'john@example.com',
            'phone': '9876543210',
            'city': 'Mumbai',
            'coverage-type': 'individual',
            'family-members': '1',
            'sum-insured': '5 Lakh',
            'payment-mode': 'monthly',
            'budget-range': 'up to 10000',
            'health-condition': 'good'
        }

        response = client.post('/get-quote', data=form_data)

        # Check response
        assert response.status_code == 200
        response_text = response.get_data(as_text=True)

        # Verify the recommendations appear in the response
        assert "Test Plan A" in response_text
        assert "Test Plan B" in response_text
        assert "₹5,000/month" in response_text
        assert "₹6,500/month" in response_text

        # Verify the recommend_plans function was called
        mock_rec.assert_called_once()

        # Check that the call included the expected payload structure
        # First argument of the first call
        call_args = mock_rec.call_args[0][0]
        assert call_args['email'] == 'john@example.com'
        assert call_args['age'] == '35'
        assert call_args['sum_insured'] == '5 Lakh'


def test_get_quote_model_unavailable_fallback(client):
    """Test that the form gracefully handles model unavailability"""

    # Mock recommend_plans to raise RuntimeError (service unavailable)
    with patch('backend.app.services.recommender.recommend_plans', side_effect=RuntimeError("Ranker unavailable")):
        # Mock get_fallback_recommendations
        fallback_recommendations = [
            {
                "plan_name": "Fallback Plan (Service Unavailable)",
                "provider": "Generic Insurance",
                "price": "₹8,500/month",
                "coverage": "₹5 Lakh",
                "rating": 4.0,
                "confidence": 75,
                "plan_id": "fallback_1",
                "deductible": 0,
                "network_size": 10000,
                "explain_text": "Popular choice while our system is updating",
                "rank": 1
            }
        ]

        with patch('backend.app.services.recommender.get_fallback_recommendations', return_value=fallback_recommendations):
            form_data = {
                'full-name': 'Jane Doe',
                'age': '28',
                'email': 'jane@example.com',
                'sum-insured': '3 Lakh',
                'budget-range': 'up to 8000'
            }

            response = client.post(
                '/get-quote', data=form_data, follow_redirects=True)

            # Should still return 200 OK with fallback results
            assert response.status_code == 200
            response_text = response.get_data(as_text=True)

            # Check for fallback content and user-friendly message
            assert "Fallback Plan" in response_text or "temporarily busy" in response_text

            # Should NOT contain hardcoded original mock data
            assert "Star Health Individual Plus" not in response_text


def test_get_quote_form_renders_correctly(client):
    """Test that the GET request renders the form correctly"""
    response = client.get('/get-quote')
    assert response.status_code == 200
    response_text = response.get_data(as_text=True)

    # Check for form elements
    assert 'form' in response_text.lower()
    assert 'get a quote' in response_text.lower() or 'quote' in response_text.lower()


def test_recommender_service_directly():
    """Test the recommender service functions directly"""
    from backend.app.services.recommender import recommend_plans, get_fallback_recommendations

    # Test fallback recommendations
    fallback = get_fallback_recommendations()
    assert isinstance(fallback, list)
    assert len(fallback) > 0
    assert all(isinstance(rec, dict) for rec in fallback)
    assert all('plan_name' in rec for rec in fallback)
    assert all('price' in rec for rec in fallback)

    # Test that fallback recommendations contain expected fields
    first_rec = fallback[0]
    required_fields = ['plan_name', 'provider', 'price',
                       'coverage', 'rating', 'confidence', 'plan_id']
    for field in required_fields:
        assert field in first_rec, f"Missing field: {field}"


def test_recommender_payload_validation():
    """Test that the recommender handles various payload formats correctly"""
    from backend.app.services.recommender import recommend_plans, get_fallback_recommendations

    # Test with minimal payload
    minimal_payload = {'email': 'test@example.com'}

    # This should either return recommendations or raise RuntimeError (both are acceptable)
    try:
        result = recommend_plans(minimal_payload, timeout=1.0)
        assert isinstance(result, list)
    except RuntimeError:
        # Service unavailable is acceptable for this test
        pass

    # Test with comprehensive payload
    full_payload = {
        'email': 'comprehensive@example.com',
        'age': '35',
        'sum_insured': '5 Lakh',
        'budget_range': 'up to 10000',
        'family_members': '2',
        'health_condition': 'good',
        'conditions': ['diabetes'],
        'city': 'Mumbai',
        'coverage_type': 'family'
    }

    try:
        result = recommend_plans(full_payload, timeout=1.0)
        assert isinstance(result, list)
        # If we get results, verify they have the expected structure
        if result:
            for rec in result:
                assert isinstance(rec, dict)
                assert 'plan_name' in rec
                assert 'price' in rec
    except RuntimeError:
        # Service unavailable is acceptable for this test
        pass


def test_get_quote_post_uses_ranker_mock(client):
    """Test that POST /get-quote uses ranker when available"""
    fake_recs = [
        {'plan_id': 'P1', 'plan_name': 'Plan One', 'monthly_premium': 100}]
    with patch('backend.app.frontend_routes.get_quote.ranker') as mock_ranker:
        mock_ranker.rank.return_value = fake_recs
        resp = client.post('/get-quote', data={'user_id': 'U1'})
        assert resp.status_code == 200
        text = resp.get_data(as_text=True)
        assert 'Plan One' in text
