# backend/app/frontend_routes/dashboard.py
from flask import Blueprint, render_template, current_app
from flask_login import current_user, login_required

frontend_bp = Blueprint(
    "frontend",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/frontend-static"
)


@frontend_bp.route("/dashboard")
@login_required
def dashboard():
    """
    Render the dashboard page with personalized recommendations.
    """
    from app.services.user_recommendations import (
        get_user_recommendations,
        explain_recommendation,
        get_user_profile_summary
    )
    
    user_id = current_user.id
    
    # Get personalized recommendations from saved leads
    try:
        plans = get_user_recommendations(user_id, limit=3)
        if not plans:
            # Fallback to sample data if no recommendations found
            current_app.logger.warning(f"No recommendations found for user {user_id}")
            plans = _get_fallback_plans()
    except Exception as e:
        current_app.logger.exception(f"Error loading recommendations: {e}")
        plans = _get_fallback_plans()
    
    # Get user profile summary
    try:
        profile_summary = get_user_profile_summary(user_id)
    except Exception:
        profile_summary = None
    
    # Get savings summary (placeholder for now)
    savings_summary = {"total_saved": 0, "year_saved": 0}
    
    # Generate explanations for each plan
    explains = []
    for p in plans:
        try:
            expl = explain_recommendation(user_id, p.get("id") or p.get("plan_id"))
        except Exception as e:
            current_app.logger.debug(f"Could not generate explanation: {e}")
            expl = {
                "why": f"This plan was recommended based on your profile analysis, "
                       f"coverage needs assessment, and premium affordability."
            }
        explains.append({
            "plan_id": p.get("id") or p.get("plan_id"),
            "explanation": expl
        })
    
    return render_template(
        "dashboard.html",
        title="Dashboard - AI-MEDPAY",
        user=current_user,
        plans=plans,
        savings_summary=savings_summary,
        explains=explains,
        profile_summary=profile_summary
    )


def _get_fallback_plans():
    """Fallback plans when no personalized recommendations are available"""
    return [
        {
            "id": "sample_1",
            "provider": "Star Health",
            "plan_name": "Super Surplus",
            "summary": "Comprehensive health coverage with 5L sum insured",
            "price": 12000,
            "badge": "Best Value"
        },
        {
            "id": "sample_2",
            "provider": "HDFC ERGO",
            "plan_name": "My Health Suraksha",
            "summary": "Family floater with wellness benefits",
            "price": 18500,
            "badge": "Popular"
        },
        {
            "id": "sample_3",
            "provider": "ICICI Lombard",
            "plan_name": "Complete Health Guard",
            "summary": "Individual plan with maternity cover",
            "price": 15200,
            "badge": "Recommended"
        }
    ]
