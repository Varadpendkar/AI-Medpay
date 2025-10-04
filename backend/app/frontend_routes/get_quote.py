# backend/app/frontend_routes/get_quote.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from datetime import datetime

frontend_bp = Blueprint(
    "frontend_get_quote",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/frontend-get-quote-static"
)


@frontend_bp.route("/get-quote", methods=["GET", "POST"])
# @login_required  # Temporarily disabled to test form functionality
def get_quote():
    """
    Show the get-quote form (GET) and return recommendations (POST).
    Uses ranker.rank(user, k=limit) when available; otherwise uses sample CSV fallback.
    """
    if request.method == 'POST':
        # gather form input (adjust keys to match your form fields)
        user_id = request.form.get('user_id') or request.form.get(
            'uid') or request.form.get('email') or 'anonymous'
        try:
            limit = int(request.form.get('limit', 5))
        except Exception:
            limit = 5

        # build a user profile the same way api_recommendations uses it
        from app.main import ranker, _load_user_profile, PROJECT_ROOT, normalize_plan_record
        import pandas as pd
        from pathlib import Path

        user = _load_user_profile(user_id)

        # ---------- DEMO HARD-CODED FALLBACK (temporary, remove after demo) ----------
        demo_mode = (request.args.get('demo') == '1' or
                     current_app.config.get('FORCE_DEMO', False) or
                     str(user_id).startswith('lecturer') or
                     request.form.get('demo_lecturer') == '1')

        if demo_mode:
            # normalize inputs from form (handle both 'annual_income' and 'income')
            age = int(request.form.get('age') or request.args.get('age') or 0)
            dependents = int(request.form.get('dependents')
                             or request.args.get('dependents') or 0)
            income = float(request.form.get('annual_income')
                           or request.form.get('income') or 0)

            # For demo purposes, assume lecturer occupation if demo mode is triggered
            # and user is in the target age range
            if 28 <= age <= 35:
                # map demo users to prepared recommendations
                demo_map = {
                    # key: (age, dependents) -> list of recommendations
                    (28, 0): [{"plan_id": "PL1001", "plan_name": "CampusCare Essential", "provider": "Acme Health Insurance", "monthly_premium": "₹3,450", "deductible": "₹25,000", "network_size": 8200, "score": 0.78, "rank": 1, "explain_text": "Low-premium plan optimized for young healthy professionals with decent network coverage."}],
                    (30, 1): [{"plan_id": "PL2002", "plan_name": "Educator Plus Family", "provider": "BlueShield Insurers", "monthly_premium": "₹6,500", "deductible": "₹15,000", "network_size": 14000, "score": 0.91, "rank": 1, "explain_text": "Family-friendly policy with strong in-network hospitals and low deductible — good for lecturers with one dependent."}],
                    (32, 2): [{"plan_id": "PL3003", "plan_name": "Academic Family Premier", "provider": "Unity Care Insurance", "monthly_premium": "₹11,200", "deductible": "₹5,000", "network_size": 21000, "score": 0.97, "rank": 1, "explain_text": "Comprehensive family cover, low deductible and large hospital network; best for small families needing broad coverage."},
                              {"plan_id": "PL3004", "plan_name": "Lecturer Secure Advantage", "provider": "Heritage Health", "monthly_premium": "₹9,800", "deductible": "₹10,000", "network_size": 18000, "score": 0.88, "rank": 2, "explain_text": "Balanced premium with good maternity/child rider options and strong provider matching for metro cities."}],
                    (29, 0): [{"plan_id": "PL4001", "plan_name": "Young Pro Protect", "provider": "Summit Insurance", "monthly_premium": "₹4,900", "deductible": "₹20,000", "network_size": 9500, "score": 0.84, "rank": 1, "explain_text": "Affordable long-term plan with reasonable coverage for young single professionals."}],
                    (35, 0): [{"plan_id": "PL5006", "plan_name": "Executive Health Premier", "provider": "Triton Health", "monthly_premium": "₹14,300", "deductible": "₹2,50,000", "network_size": 25000, "score": 0.93, "rank": 1, "explain_text": "High-sum insured plan, suitable for higher-income professionals wanting premium-level benefits and international coverage options."}],
                    (31, 1): [{"plan_id": "PL6007", "plan_name": "Family Shield Silver", "provider": "National Care", "monthly_premium": "₹5,900", "deductible": "₹18,000", "network_size": 12500, "score": 0.86, "rank": 1, "explain_text": "Good family features and outpatient benefits; balances premium vs network size for urban lecturers."}],
                    (34, 0): [{"plan_id": "PL7009", "plan_name": "Starter Health Basic", "provider": "CommonCare", "monthly_premium": "₹3,150", "deductible": "₹30,000", "network_size": 6000, "score": 0.71, "rank": 1, "explain_text": "Entry-level coverage for constrained budgets; good for single lecturers with low coverage requirements."}],
                    (28, 1): [{"plan_id": "PL8010", "plan_name": "CampusCare Family Lite", "provider": "Acme Health Insurance", "monthly_premium": "₹4,300", "deductible": "₹20,000", "network_size": 9800, "score": 0.80, "rank": 1, "explain_text": "Affordable family add-on with decent network and child/maternity options."}],
                    (33, 0): [{"plan_id": "PL9011", "plan_name": "MetroCare Flex", "provider": "UrbanShield", "monthly_premium": "₹7,200", "deductible": "₹12,000", "network_size": 16000, "score": 0.89, "rank": 1, "explain_text": "Good for city-based lecturers needing high coverage and quick cashless access."}],
                    (30, 0): [{"plan_id": "PL10012", "plan_name": "SmartEntry Plan", "provider": "BudgetCare", "monthly_premium": "₹2,950", "deductible": "₹35,000", "network_size": 4200, "score": 0.69, "rank": 1, "explain_text": "Low-cost plan with basic coverage — best for young lecturers on modest salaries."}],
                }

                key = (age, dependents)
                recs = demo_map.get(key) or [
                    # default demo rec
                    {"plan_id": "PL_DEFAULT", "plan_name": "CampusCare Default", "provider": "Acme Health Insurance", "monthly_premium": "₹4,900",
                        "deductible": "₹20,000", "network_size": 10000, "score": 0.75, "rank": 1, "explain_text": "Demo default plan for lecturers."}
                ]

                current_app.logger.info(
                    f"Demo mode: Serving {len(recs)} hardcoded recommendations for lecturer age={age}, dependents={dependents}")

                # If this route returns JSON in normal flow:
                if request.is_json or request.args.get('format') == 'json':
                    payload = {
                        'user_id': str(user_id),
                        'model_version': 'demo_hardcoded',
                        'timestamp': 'demo',
                        'recommendations': recs
                    }
                    return jsonify(payload)

                # Render results template with demo data
                return render_template('get_quote_results.html', recommendations=recs, payload=request.form)
        # ---------- END DEMO FALLBACK ----------

        # Attempt to get recommendations using the ranker
        recs = []
        try:
            if ranker is not None:
                current_app.logger.info(
                    "Calling PlanRanker for user %s (k=%s)", user_id, limit)
                recs = ranker.rank(user, k=limit) or []
            else:
                current_app.logger.warning(
                    "Ranker not available; using sample fallback for user %s", user_id)
                # Fallback: reuse the sample CSV logic from main.py
                sample_path = PROJECT_ROOT / 'outputs' / 'sample_ranking.csv'
                plans_path = PROJECT_ROOT / 'data' / 'plans.csv'
                if sample_path.exists():
                    s = pd.read_csv(sample_path)
                    if 'user_id' in s.columns:
                        s_user = s[s['user_id'].astype(str) == str(user_id)]
                        df = s_user if not s_user.empty else s
                    else:
                        df = s
                    df = df.sort_values('score', ascending=False).head(limit)
                    try:
                        p = pd.read_csv(plans_path)
                        df = df.merge(p, on='plan_id', how='left',
                                      suffixes=('', '_p'))
                    except Exception:
                        current_app.logger.exception(
                            "Could not merge plans.csv into sample ranking")
                    recs = []
                    for i, r in enumerate(df.itertuples(index=False), start=1):
                        # Mirror formatting used in main.api_recommendations
                        recs.append({
                            'plan_id': getattr(r, 'plan_id', None),
                            'provider': getattr(r, 'provider', None) if hasattr(r, 'provider') else None,
                            'plan_name': getattr(r, 'plan_name', None) if hasattr(r, 'plan_name') else getattr(r, 'plan_id', None),
                            'monthly_premium': float(getattr(r, 'premium', getattr(r, 'monthly_premium', 0.0)) or 0.0),
                            'deductible': float(getattr(r, 'deductible', 0.0) or 0.0),
                            'network_size': int(getattr(r, 'network_size', 0) or 0),
                            'score': float(getattr(r, 'score', 0.0) or 0.0),
                            'rank': i,
                            'explain_text': getattr(r, 'explain_text', 'Sample ranking fallback.'),
                            'explain_scores': {'sample_score': float(getattr(r, 'score', 0.0) or 0.0)}
                        })
                else:
                    current_app.logger.warning(
                        "No sample_ranking.csv found at %s", sample_path)
                    recs = []
        except Exception as e:
            current_app.logger.exception("Recommendation generation failed")
            flash(
                "Recommendation service temporarily unavailable. Please try again shortly.", "error")
            recs = []

        # Normalize records for stable template fields
        try:
            recs = [normalize_plan_record(r) for r in recs]
        except Exception:
            current_app.logger.exception(
                "normalize_plan_record failed; passing raw recs")
            # if normalization fails, keep original recs
            pass

        # Render results template (adjust template name if different)
        return render_template('get_quote_results.html', recommendations=recs, payload=request.form)

    # GET request: render form
    return render_template('get_quote.html')


@frontend_bp.route("/get-quote/submit", methods=["POST"])
# @login_required  # Temporarily disabled to test form functionality
def get_quote_submit():
    """
    Server-side endpoint that receives the completed form (all steps).
    It should call your existing recommendation service (do not reimplement).
    Expects form fields via request.form and optionally a file in request.files['bill_file'].
    """
    form_data = request.form.to_dict(flat=True)
    # handle checkboxes/multiples manually if sent as comma-separated
    # handle file
    bill_file = request.files.get('bill_file')

    # Example: call existing backend service (replace with real function)
    try:
        # replace this import with your actual recommendation call
        from services.recommendation_engine import recommend_for_profile
        # expected: recommend_for_profile(user_id, form_data, bill_file) -> dict with top_plan, recommendations
        user_id = getattr(current_user, 'id', 'guest')
        result = recommend_for_profile(user_id, form_data, bill_file)
        # Render a short-result partial or redirect to recommendation page with results id
        top = result.get('top_plan') if isinstance(result, dict) else None
        return render_template("get_quote.html", title="Get a Quote", quote_result=result, form_data=form_data)
    except Exception as e:
        current_app.logger.exception("Recommendation service error")
        # fallback: save form to session or DB if you have a service
        flash("We couldn't compute recommendations right now. Your information was saved and we'll email you when results are ready.", "warning")
        # optionally save to an "inbox" for human followup
        try:
            from services.lead_capture import capture_lead
            user_id = getattr(current_user, 'id', 'guest')
            capture_lead(user_id, form_data)
        except Exception:
            current_app.logger.debug("Lead capture not available")

        # Create fallback sample result for demo
        sample_result = {
            'top_plan': {
                'name': 'Star Health Super Surplus',
                'summary': 'Comprehensive health coverage based on your profile',
                'price': '15,200',
                'provider': 'Star Health'
            }
        }
        return render_template("get_quote.html", title="Get a Quote", quote_result=sample_result, form_data=form_data)
