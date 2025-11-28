# app/services/persistence.py
"""
Persistence layer for storing Get Quote submissions and recommendations.
Stores leads in SQLite for analytics, retraining, and user journey tracking.
"""
import sqlite3
import os
import json
import logging

LOG = logging.getLogger(__name__)

# Path to leads database
DB = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(__file__))), 'data', 'leads.db')
os.makedirs(os.path.dirname(DB), exist_ok=True)


def _conn():
    """Create database connection with Row factory for dict-like access"""
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def save_lead_and_recs(user_id, profile_dict, recommendations_list, ip=None, source=None):
    """
    Store a Get Quote submission (lead) and the recommended plans returned.

    Args:
        user_id: User identifier (session ID, email, or anonymous UUID)
        profile_dict: Serializable dict of user profile features used by ranker
        recommendations_list: List of dicts with plan_id, plan_name, provider, score
        ip: Optional IP address of requester
        source: Optional source identifier (e.g., 'get_quote', 'api', 'demo')

    Returns:
        lead_id: Integer primary key of created lead record

    Example:
        lead_id = save_lead_and_recs(
            user_id='user_123',
            profile_dict={'age': 35, 'income': 600000, 'city': 'Mumbai'},
            recommendations_list=[
                {'plan_id': 'PL001', 'plan_name': 'Health Plus', 'provider': 'HDFC', 'score': 0.95},
                {'plan_id': 'PL002', 'plan_name': 'Family Care', 'provider': 'Star', 'score': 0.87}
            ],
            ip='192.168.1.1',
            source='get_quote'
        )
    """
    try:
        conn = _conn()
        cur = conn.cursor()

        # Insert lead record
        cur.execute(
            "INSERT INTO leads (user_id, profile_json, ip, source) VALUES (?,?,?,?)",
            (user_id, json.dumps(profile_dict), ip or '', source or 'web')
        )
        lead_id = cur.lastrowid

        # Insert recommendation records for this lead
        for i, r in enumerate(recommendations_list, start=1):
            cur.execute("""
              INSERT INTO recommendations (lead_id, rank, plan_id, plan_name, provider, model_score)
              VALUES (?,?,?,?,?,?)
            """, (
                lead_id,
                i,
                r.get('plan_id') or r.get('planid') or '',
                r.get('plan_name') or r.get('name') or '',
                r.get('provider') or '',
                float(r.get('score') or r.get('model_score')
                      or r.get('raw_score') or 0.0)
            ))

        conn.commit()
        conn.close()

        LOG.info("✅ Saved lead %s for user %s with %d recommendations",
                 lead_id, user_id, len(recommendations_list))
        return lead_id

    except Exception as e:
        LOG.exception("❌ Failed to save lead for user %s: %s", user_id, e)
        raise


def get_lead_stats():
    """
    Get summary statistics about stored leads.
    Useful for analytics dashboard.

    Returns:
        dict with total_leads, total_recommendations, recent_leads count
    """
    try:
        conn = _conn()
        cur = conn.cursor()

        total_leads = cur.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        total_recs = cur.execute(
            "SELECT COUNT(*) FROM recommendations").fetchone()[0]
        recent = cur.execute(
            "SELECT COUNT(*) FROM leads WHERE timestamp > datetime('now', '-7 days')"
        ).fetchone()[0]

        conn.close()

        return {
            'total_leads': total_leads,
            'total_recommendations': total_recs,
            'recent_leads_7d': recent
        }
    except sqlite3.Error as e:
        LOG.exception("Failed to get lead stats: %s", e)
        return {'total_leads': 0, 'total_recommendations': 0, 'recent_leads_7d': 0}
