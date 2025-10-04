# backend/app/services/recommender.py
import logging
import requests
from typing import Dict, Any, List
from requests.exceptions import RequestException, Timeout
from flask import current_app, request
import json

logger = logging.getLogger(__name__)


def recommend_plans(payload: Dict[str, Any], timeout: float = 5.0) -> List[Dict[str, Any]]:
    """
    Call the model / api to get recommendations.
    Returns list of recommended plan dicts on success.
    Raises RuntimeError on failure (caller will handle fallback).
    """
    try:
        # Use internal API endpoint instead of external HTTP call
        # Import the ranker and _load_user_profile functions
        from app.main import ranker, _load_user_profile

        # Extract user information from payload
        user_id = payload.get('email', 'guest_user')

        # Load base user profile and update with form data
        user_profile = _load_user_profile(user_id)

        # Update profile with form data
        if 'age' in payload and payload['age']:
            try:
                user_profile['age'] = int(payload['age'])
            except (ValueError, TypeError):
                pass

        # Map form fields to profile fields
        if 'sum_insured' in payload and payload['sum_insured']:
            try:
                # Convert sum insured to numeric value
                sum_insured = payload['sum_insured']
                if 'lakh' in str(sum_insured).lower():
                    # Extract number and convert to lakhs
                    import re
                    match = re.search(r'(\d+)', str(sum_insured))
                    if match:
                        user_profile['target_coverage'] = int(
                            match.group(1)) * 100000
                elif 'crore' in str(sum_insured).lower():
                    match = re.search(r'(\d+)', str(sum_insured))
                    if match:
                        user_profile['target_coverage'] = int(
                            match.group(1)) * 10000000
                else:
                    user_profile['target_coverage'] = int(
                        payload['sum_insured'])
            except (ValueError, TypeError):
                pass

        if 'budget_range' in payload and payload['budget_range']:
            try:
                # Extract max premium from budget range
                budget = payload['budget_range']
                if 'up to' in str(budget).lower():
                    import re
                    match = re.search(r'(\d+)', str(budget))
                    if match:
                        user_profile['max_premium'] = int(
                            match.group(1)) * 12  # Assuming yearly
                else:
                    user_profile['max_premium'] = int(budget) * 12
            except (ValueError, TypeError):
                pass

        # Update health status based on conditions
        conditions = payload.get('conditions', [])
        if conditions and len(conditions) > 0:
            user_profile['health_status'] = 'poor' if len(
                conditions) > 2 else 'average'
        elif payload.get('health_condition') == 'excellent':
            user_profile['health_status'] = 'good'

        # Update dependents count
        if 'family_members' in payload and payload['family_members']:
            try:
                family_count = int(payload['family_members'])
                user_profile['dependents'] = max(
                    0, family_count - 1)  # Exclude self
            except (ValueError, TypeError):
                pass

        # Call the ranker if available
        if ranker is not None:
            logger.info(f"Calling ranker with user profile: {user_profile}")
            raw_recommendations = ranker.rank(user_profile, k=5)

            # Convert to expected format
            recommendations = []
            for i, rec in enumerate(raw_recommendations[:3]):  # Limit to top 3
                # Normalize the record
                from app.main import normalize_plan_record, safe_num
                rec = normalize_plan_record(rec)

                # Calculate display values
                monthly_premium = safe_num(
                    rec, 'monthly_premium', 'premium', default=5000)
                coverage = safe_num(rec, 'coverage_amount',
                                    'sum_insured', default=500000)
                score = safe_num(rec, 'score', default=0.7)

                recommendations.append({
                    'plan_name': rec.get('plan_name', f'Plan {i+1}'),
                    'provider': rec.get('provider', 'Insurance Provider'),
                    'price': f'₹{monthly_premium:,.0f}/month',
                    'coverage': f'₹{coverage/100000:.0f} Lakh' if coverage < 10000000 else f'₹{coverage/10000000:.1f} Crore',
                    # Convert score to 1-5 rating
                    'rating': min(5.0, max(1.0, score * 5)),
                    'confidence': min(99, max(50, int(score * 100))),
                    'plan_id': rec.get('plan_id', f'plan_{i+1}'),
                    'deductible': safe_num(rec, 'deductible', default=0),
                    'network_size': safe_num(rec, 'network_size', default=1000),
                    'explain_text': rec.get('explain_text', 'Recommended based on your profile'),
                    'rank': i + 1
                })

            if recommendations:
                logger.info(
                    f"Successfully generated {len(recommendations)} recommendations")
                return recommendations

        # If ranker is None or returned empty results, raise error to trigger fallback
        logger.warning("Ranker unavailable or returned no results")
        raise RuntimeError("Ranker unavailable or returned no results")

    except Exception as e:
        logger.exception("Recommender service failed")
        raise RuntimeError(f"Recommender unavailable: {str(e)}") from e


def get_fallback_recommendations() -> List[Dict[str, Any]]:
    """
    Generate fallback recommendations when the model is unavailable.
    These are generic but reasonable recommendations.
    """
    return [
        {
            'plan_name': 'Star Health Super Surplus (Fallback)',
            'provider': 'Star Health Insurance',
            'price': '₹8,500/month',
            'coverage': '₹5 Lakh',
            'rating': 4.2,
            'confidence': 75,
            'plan_id': 'fallback_1',
            'deductible': 0,
            'network_size': 12000,
            'explain_text': 'Popular choice with comprehensive coverage and wide hospital network.',
            'rank': 1
        },
        {
            'plan_name': 'HDFC ERGO My Health Suraksha (Fallback)',
            'provider': 'HDFC ERGO',
            'price': '₹7,200/month',
            'coverage': '₹3 Lakh',
            'rating': 4.0,
            'confidence': 72,
            'plan_id': 'fallback_2',
            'deductible': 5000,
            'network_size': 10000,
            'explain_text': 'Affordable option with good network coverage and reasonable deductible.',
            'rank': 2
        },
        {
            'plan_name': 'Care Health Supreme (Fallback)',
            'provider': 'Care Health Insurance',
            'price': '₹9,800/month',
            'coverage': '₹10 Lakh',
            'rating': 4.3,
            'confidence': 78,
            'plan_id': 'fallback_3',
            'deductible': 0,
            'network_size': 15000,
            'explain_text': 'Premium plan with high coverage amount and extensive hospital network.',
            'rank': 3
        }
    ]
