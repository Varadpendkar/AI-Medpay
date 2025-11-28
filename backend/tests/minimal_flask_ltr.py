#!/usr/bin/env python3
"""
Minimal Flask app to test LTR model integration with get-quote endpoint.
"""
from utils.simple_ranker import PlanRanker
import pandas as pd
from flask import Flask, request, render_template, jsonify
import sys
from pathlib import Path

# Add the backend/app directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'backend' / 'app'))

# Now import after path is set


# Initialize Flask app
app = Flask(__name__,
            template_folder='backend/app/frontend_routes/templates',
            static_folder='backend/app/frontend_routes/static')

# Initialize ranker
PROJECT_ROOT = Path(__file__).parent / 'backend' / 'app'
try:
    ranker = PlanRanker(PROJECT_ROOT)
    print("✅ PlanRanker initialized successfully")
except Exception as e:
    print(f"❌ PlanRanker initialization failed: {e}")
    ranker = None


def _load_user_profile(form_data):
    """Extract user profile from form data."""
    return {
        'age': int(form_data.get('age', 30)),
        'dependents': int(form_data.get('dependents', 0)),
        'income': 1000000,  # Default income
        'risk_score': 0.3,
        'state': form_data.get('location', ''),
        'max_premium': float(form_data.get('max_premium', 0)) if form_data.get('max_premium') else None
    }


def normalize_plan_record(plan):
    """Normalize plan record for display."""
    normalized = {
        'plan_id': plan.get('plan_id', ''),
        'plan_name': plan.get('plan_name', 'Unknown Plan'),
        'provider': plan.get('provider', ''),
        'monthly_premium': int(plan.get('premium', 0) / 12) if plan.get('premium') else 0,
        'annual_premium': int(plan.get('premium', 0)),
        'deductible': int(plan.get('deductible', 0)),
        'copay': int(plan.get('copay', 0)),
        'coverage_amount': int(plan.get('coverage_amount', 0)),
        'network_size': int(plan.get('network_size', 0)),
        'score': round(float(plan.get('score', 0)), 3),
        'bullets': plan.get('bullets', [])
    }
    return normalized


@app.route('/')
def home():
    """Home page."""
    return '<h1>LTR Model Test Server</h1><p><a href="/get-quote">Go to Get Quote</a></p>'


@app.route('/get-quote', methods=['GET', 'POST'])
def get_quote():
    """Get quote page and form handler."""
    if request.method == 'GET':
        # Return simple form for testing
        return '''
        <h2>Get Quote - LTR Model Test</h2>
        <form method="POST">
            <p>Age: <input type="number" name="age" value="32" required></p>
            <p>Dependents: <input type="number" name="dependents" value="2"></p>
            <p>Location: <input type="text" name="location" value="Mumbai"></p>
            <p>Max Premium: <input type="number" name="max_premium" value="15000"></p>
            <p>Coverage Amount: <input type="number" name="coverage_amount" value="1000000"></p>
            <p><input type="submit" value="Get Recommendations"></p>
        </form>
        '''

    # POST request - get recommendations
    try:
        if not ranker:
            return jsonify({'error': 'Ranker not available'}), 500

        # Extract user profile
        user_profile = _load_user_profile(request.form)

        # Get recommendations
        raw_recommendations = ranker.rank(user_profile, k=8)

        if not raw_recommendations:
            return jsonify({'error': 'No recommendations found'}), 404

        # Normalize recommendations
        recommendations = [normalize_plan_record(
            plan) for plan in raw_recommendations]

        # Return simple HTML response
        html = '<h2>Recommendations (LTR Model)</h2>'
        html += f'<p>Found {len(recommendations)} recommendations for user profile:</p>'
        html += f'<p>Age: {user_profile["age"]}, Dependents: {user_profile["dependents"]}, Max Premium: {user_profile.get("max_premium", "No limit")}</p>'
        html += '<table border="1" style="border-collapse: collapse; width: 100%;">'
        html += '<tr><th>Plan</th><th>Provider</th><th>Monthly Premium</th><th>Deductible</th><th>Coverage</th><th>Score</th><th>Benefits</th></tr>'

        for i, rec in enumerate(recommendations, 1):
            benefits = '<br>'.join(rec['bullets'][:3])  # Show top 3 benefits
            html += f'''
            <tr>
                <td>{i}. {rec['plan_name']}</td>
                <td>{rec['provider']}</td>
                <td>₹{rec['monthly_premium']:,}</td>
                <td>₹{rec['deductible']:,}</td>
                <td>₹{rec['coverage_amount']:,}</td>
                <td>{rec['score']}</td>
                <td>{benefits}</td>
            </tr>
            '''

        html += '</table>'
        html += '<p><a href="/get-quote">Try another query</a></p>'

        return html

    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500


if __name__ == '__main__':
    print("Starting minimal Flask server for LTR model testing...")
    print("Visit http://127.0.0.1:5001/get-quote to test")
    app.run(debug=True, port=5001)
