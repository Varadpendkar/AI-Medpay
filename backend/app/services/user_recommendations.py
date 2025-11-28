"""
User Recommendations Service

Retrieves personalized plan recommendations for authenticated users
based on their profile and saved lead data.
"""
import sqlite3
import os
import json
import logging
from typing import List, Dict, Optional

LOG = logging.getLogger(__name__)


def get_user_recommendations(user_id: int, limit: int = 5) -> List[Dict]:
    """
    Get personalized plan recommendations for a user from saved leads.
    
    Args:
        user_id: User ID from the users table
        limit: Maximum number of recommendations to return
        
    Returns:
        List of recommendation dicts with plan details and explanations
    """
    # Path to leads database
    leads_db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'data',
        'leads.db'
    )
    
    if not os.path.exists(leads_db_path):
        LOG.warning(f"Leads database not found at {leads_db_path}")
        return []
    
    try:
        conn = sqlite3.connect(leads_db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Find the most recent lead for this user
        lead = cur.execute("""
            SELECT * FROM leads 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (str(user_id),)).fetchone()
        
        if not lead:
            LOG.info(f"No leads found for user {user_id}")
            conn.close()
            return []
        
        lead_id = lead['id']
        profile_data = json.loads(lead['profile_json']) if lead['profile_json'] else {}
        
        # Get recommendations for this lead
        recs = cur.execute("""
            SELECT * FROM recommendations 
            WHERE lead_id = ? 
            ORDER BY rank 
            LIMIT ?
        """, (lead_id, limit)).fetchall()
        
        conn.close()
        
        # Format recommendations with explanations
        recommendations = []
        for rec in recs:
            plan_dict = {
                'id': rec['plan_id'],
                'plan_id': rec['plan_id'],
                'rank': rec['rank'],
                'plan_name': rec['plan_name'],
                'provider': rec['provider'],
                'score': rec['model_score'],
                'badge': _get_badge(rec['rank']),
                'summary': _generate_summary(rec, profile_data)
            }
            recommendations.append(plan_dict)
        
        LOG.info(f"Retrieved {len(recommendations)} recommendations for user {user_id}")
        return recommendations
        
    except Exception as e:
        LOG.exception(f"Error retrieving recommendations for user {user_id}: {e}")
        return []


def explain_recommendation(user_id: int, plan_id: str) -> Dict:
    """
    Generate detailed explanation for why a specific plan was recommended.
    
    Args:
        user_id: User ID
        plan_id: Plan ID to explain
        
    Returns:
        Dict with explanation details
    """
    leads_db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'data',
        'leads.db'
    )
    
    if not os.path.exists(leads_db_path):
        return {"why": "Recommendation based on your profile analysis."}
    
    try:
        conn = sqlite3.connect(leads_db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Find the lead and recommendation
        lead = cur.execute("""
            SELECT l.*, r.plan_name, r.provider, r.rank, r.model_score
            FROM leads l
            JOIN recommendations r ON l.id = r.lead_id
            WHERE l.user_id = ? AND r.plan_id = ?
            ORDER BY l.timestamp DESC
            LIMIT 1
        """, (str(user_id), plan_id)).fetchone()
        
        conn.close()
        
        if not lead:
            return {"why": "This plan matches your health profile and budget."}
        
        profile_data = json.loads(lead['profile_json']) if lead['profile_json'] else {}
        
        # Generate detailed explanation
        explanation = _generate_detailed_explanation(lead, profile_data)
        
        return explanation
        
    except Exception as e:
        LOG.exception(f"Error explaining recommendation: {e}")
        return {"why": "This plan was selected based on your profile."}


def _get_badge(rank: int) -> str:
    """Get display badge based on rank"""
    if rank == 1:
        return "Best Value"
    elif rank == 2:
        return "Popular"
    elif rank == 3:
        return "Recommended"
    else:
        return "Good Option"


def _generate_summary(rec: sqlite3.Row, profile: Dict) -> str:
    """Generate one-line summary for a recommendation"""
    age = profile.get('age', 'N/A')
    income = profile.get('annual_income', 0)
    conditions = []
    if profile.get('has_diabetes'):
        conditions.append('diabetes')
    if profile.get('has_hypertension'):
        conditions.append('hypertension')
    if profile.get('has_obesity'):
        conditions.append('obesity')
    
    conditions_str = ', '.join(conditions) if conditions else 'no pre-existing conditions'
    
    return f"Personalized for {age}yr old with {conditions_str}, " \
           f"optimized for ₹{income:,.0f} annual income"


def _generate_detailed_explanation(lead: sqlite3.Row, profile: Dict) -> Dict:
    """Generate detailed explanation with multiple factors"""
    
    # Extract profile details
    age = profile.get('age', 0)
    income = profile.get('annual_income', 0)
    budget = profile.get('premium_budget', 0)
    coverage = profile.get('coverage_amount', 0)
    city = profile.get('city', 'your location')
    
    # Health conditions
    conditions = []
    if profile.get('has_diabetes'):
        conditions.append('Diabetes')
    if profile.get('has_hypertension'):
        conditions.append('Hypertension')
    if profile.get('has_obesity'):
        conditions.append('Obesity')
    if profile.get('has_heart_disease'):
        conditions.append('Heart Disease')
    if profile.get('has_cancer_history'):
        conditions.append('Cancer History')
    
    conditions_str = ', '.join(conditions) if conditions else 'no pre-existing conditions'
    
    # Generate explanation
    why_text = f"""This plan was recommended based on comprehensive analysis of your profile:

**Health Profile**: Age {age} with {conditions_str}. The plan offers coverage tailored to your specific health needs.

**Financial Fit**: With an annual income of ₹{income:,.0f} and budget of ₹{budget:,}/month, this plan provides excellent value at {lead['rank']} position in our recommendations.

**Coverage**: Provides ₹{coverage:,.0f} coverage aligned with your requirements in {city}.

**AI Confidence**: Our machine learning model scored this plan {lead['model_score']:.2f}, indicating strong suitability based on {profile.get('claim_history_count', 0)} previous claims and {profile.get('renewal_loyalty_years', 0)} years of insurance history.

**Provider**: {lead['provider']} offers reliable service with good network coverage in your area."""
    
    return {
        "why": why_text,
        "factors": {
            "age_match": f"{age} years",
            "health_conditions": conditions_str,
            "income_compatibility": f"₹{income:,.0f}/year",
            "budget_fit": f"₹{budget:,}/month",
            "coverage_amount": f"₹{coverage:,.0f}",
            "model_confidence": f"{lead['model_score']:.1%}",
            "rank": f"#{lead['rank']} recommended"
        }
    }


def get_user_profile_summary(user_id: int) -> Optional[Dict]:
    """
    Get user profile summary from user_profiles table.
    
    Args:
        user_id: User ID
        
    Returns:
        Dict with profile summary or None
    """
    try:
        from app.models.models import db
        from sqlalchemy import text
        
        with db.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT age, gender, city, state, annual_income, 
                           premium_budget, has_diabetes, has_hypertension,
                           has_obesity, has_heart_disease, coverage_amount
                    FROM user_profiles 
                    WHERE user_id = :user_id
                """),
                {"user_id": user_id}
            ).fetchone()
            
            if not result:
                return None
            
            # Convert to dict
            profile = dict(result._mapping)
            
            # Add computed fields
            conditions = []
            if profile.get('has_diabetes'):
                conditions.append('Diabetes')
            if profile.get('has_hypertension'):
                conditions.append('Hypertension')
            if profile.get('has_obesity'):
                conditions.append('Obesity')
            if profile.get('has_heart_disease'):
                conditions.append('Heart Disease')
            
            profile['health_conditions'] = ', '.join(conditions) if conditions else 'None'
            
            return profile
            
    except Exception as e:
        LOG.exception(f"Error getting profile summary for user {user_id}: {e}")
        return None
