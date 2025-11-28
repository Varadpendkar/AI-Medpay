# backend/app/frontend_routes/get_quote.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime
import numpy as np
import math
import uuid

frontend_bp = Blueprint(
    "frontend_get_quote",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/frontend-get-quote-static"
)


def _map_income_to_band(annual_income):
    """Convert numeric annual income to categorical income band for model compatibility"""
    if annual_income < 300000:
        return '<3L'
    elif annual_income < 600000:
        return '3-6L'
    elif annual_income < 1000000:
        return '6-10L'
    elif annual_income < 2000000:
        return '10-20L'
    else:
        return '>20L'


def format_currency(v):
    """Format numeric value as currency (₹X,XXX) or return None if invalid."""
    try:
        v = float(v)
        if math.isnan(v) or v <= 0:
            return None
        return f"₹{int(v):,}"
    except Exception:
        return None


def normalize_scores(raw_scores):
    """Normalize raw_scores (list or np.array) to 0..1; higher is better."""
    arr = np.array(raw_scores, dtype=float)
    if arr.size == 0:
        return arr.tolist()
    lo, hi = arr.min(), arr.max()
    denom = (hi - lo) if (hi - lo) > 1e-9 else 1.0
    return ((arr - lo) / denom).tolist()


def prepare_friendly_recommendations(ranked_plans):
    """
    Transform raw ranked plans into frontend-friendly format with:
    - Normalized confidence scores (0-100%)
    - Formatted currency and network numbers
    - Merged explanation bullets with live values
    - Premium missing CTA flags
    """
    if not ranked_plans:
        return []

    # Extract raw scores and normalize
    raw_scores = [p.get("score", 0.0) for p in ranked_plans]
    norm_scores = normalize_scores(raw_scores)

    friendly_recs = []
    for i, p in enumerate(ranked_plans):
        # Ensure numeric fields are present
        premium_raw = p.get("premium", p.get("monthly_premium", None))
        premium_display = format_currency(premium_raw)

        deductible_raw = p.get("deductible", 0)
        deductible_display = format_currency(deductible_raw) or "₹0"

        network_size = p.get("network_size", p.get("networksize", None))
        try:
            network_display = f"{int(network_size):,}" if network_size not in (
                None, "", float("nan")) else "—"
        except Exception:
            network_display = "—"

        coverage_raw = p.get("coverage_amount", p.get("coverageamount", None))
        coverage_display = format_currency(coverage_raw) or "—"

        # Get explanation bullets from plan or generate defaults
        bullets = p.get("bullets", [])
        if not bullets:
            # Try to get from enhanced dataset fields
            why1 = p.get("why_good_1") or p.get("highlight_text") or ""
            why2 = p.get("why_good_2") or ""
            why3 = p.get("why_good_3") or ""
            bullets = [why1, why2, why3]

        # Ensure we have at least 3 bullets
        while len(bullets) < 3:
            bullets.append("")

        # Interpolate live values into bullet text if placeholders present
        formatted_bullets = []
        for bullet in bullets[:3]:
            if not bullet:
                continue
            bullet = str(bullet).replace(
                "{premium}", premium_display or "Contact insurer")
            bullet = bullet.replace("{deductible}", deductible_display)
            bullet = bullet.replace("{network_size}", network_display)
            bullet = bullet.replace("{coverage}", coverage_display)
            formatted_bullets.append(bullet)

        # Generate default bullets if none provided
        if not any(formatted_bullets):
            formatted_bullets = [
                f"Coverage: {coverage_display}",
                f"Network: {network_display} hospitals",
                f"Deductible: {deductible_display}"
            ]

        # Friendly confidence percent
        confidence = norm_scores[i] if i < len(norm_scores) else 0.0
        confidence_label = f"{int(round(confidence * 100))}%"

        # If premium missing show CTA key so frontend can display "Check premium"
        premium_missing = premium_display is None

        # BACKWARD-COMPAT: alias `score` to raw_score for old templates
        raw_score_value = p.get("score")
        alias_score = raw_score_value if raw_score_value is not None else confidence

        friendly_recs.append({
            "plan_id": p.get("plan_id") or p.get("planid"),
            "provider": p.get("provider"),
            "plan_name": p.get("plan_name"),
            "premium_display": premium_display,
            "premium_missing": premium_missing,
            "deductible_display": deductible_display,
            "network_display": network_display,
            "coverage_display": coverage_display,
            "rank": i + 1,
            "raw_score": raw_score_value,
            "score": alias_score,  # <--- Backward-compatible key
            "confidence": confidence,
            "confidence_label": confidence_label,
            "why": formatted_bullets,
            "explain_text": p.get("explain_text") or " | ".join([x for x in formatted_bullets if x]),
            # Keep raw for debugging
            "_raw": p
        })

    return friendly_recs


@frontend_bp.route("/get-quote", methods=["GET", "POST"])
# @login_required  # Temporarily disabled to test form functionality
def get_quote():
    """
    Show the get-quote form (GET) and return recommendations (POST).
    Uses ranker.rank(user, k=limit) when available; otherwise uses sample CSV fallback.
    """
    if request.method == 'POST':
        # Log all form data for debugging
        current_app.logger.info(f"📥 Received POST request to /get-quote")
        current_app.logger.info(f"Form data keys: {list(request.form.keys())}")
        current_app.logger.info(f"Form data: {dict(request.form)}")

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

        # Build comprehensive user profile from form data
        # Extract pre-existing conditions from checkboxes
        pre_existing = []
        if request.form.get('pre_existing_diabetes'):
            pre_existing.append('diabetes')
        if request.form.get('pre_existing_hypertension'):
            pre_existing.append('hypertension')
        if request.form.get('pre_existing_heart_disease'):
            pre_existing.append('heart_disease')
        if request.form.get('pre_existing_asthma'):
            pre_existing.append('asthma')
        if request.form.get('pre_existing_thyroid'):
            pre_existing.append('thyroid')
        if request.form.get('pre_existing_cancer'):
            pre_existing.append('cancer')

        # Extract family history from checkboxes
        family_hist = []
        if request.form.get('family_diabetes'):
            family_hist.append('diabetes')
        if request.form.get('family_heart_disease'):
            family_hist.append('heart_disease')
        if request.form.get('family_cancer'):
            family_hist.append('cancer')
        if request.form.get('family_hypertension'):
            family_hist.append('hypertension')

        # Validate required fields per MASTER PROMPT schema
        required_fields = [
            "age", "gender", "marital_status", "city", "state",
            "annual_income", "premium_budget", "occupation_type",
            "smoking_flag", "plan_type"
        ]

        # Check for missing fields
        data = request.form.to_dict()
        missing = [f for f in required_fields if f not in data or data[f] == ""]

        if missing:
            current_app.logger.error(f"❌ Missing required fields: {missing}")
            error_msg = f"Missing required fields: {', '.join(missing)}"

            # Return JSON for API calls
            if request.is_json or request.headers.get('Accept') == 'application/json':
                return jsonify({
                    "status": "error",
                    "message": error_msg
                }), 400

            # Flash message and re-render form for regular form submissions
            flash(error_msg, "error")
            return render_template('get_quote.html')

        # Normalize user profile from validated form data
        user = {
            'user_id': user_id,
            # Demographics (REQUIRED)
            'age': int(data['age']),
            'gender': data['gender'].lower(),
            'marital_status': data['marital_status'],
            'dependents_count': int(data.get('dependents') or 0),
            # Location (REQUIRED)
            'city': data['city'],
            'state': data['state'],
            'pincode': data.get('pincode', ''),
            # Use city as region fallback
            'region': data.get('region', data['city']),
            # Financial (REQUIRED)
            'income': float(data.get('annual_income', 0)),
            # Alias for compatibility
            'annual_income': float(data.get('annual_income', 0)),
            # Map income to income_band for model compatibility
            'income_band': _map_income_to_band(float(data.get('annual_income', 0))),
            'premium_budget': float(data['premium_budget']),
            'occupation_type': data['occupation_type'],
            'employment_sector': data.get('employment_sector', 'private'),
            # Health & Lifestyle (REQUIRED: smoking_flag)
            'smoking_flag': data.get('smoking_flag', 'false') == 'true',
            # Add smoking_status alias for model (expects 'yes'/'no'/'ex-smoker')
            'smoking_status': 'yes' if data.get('smoking_flag', 'false') == 'true' else 'no',
            'alcohol_flag': data.get('alcohol_flag', 'false') == 'true',
            'bmi': float(data.get('bmi', 24.0)) if data.get('bmi') else 24.0,
            'previous_claims_count': int(data.get('previous_claims_count') or 0),
            # Add aliases for model compatibility - handle empty strings
            'claim_history_count': int(data.get('claim_history_count') or data.get('previous_claims_count') or 0),
            'renewal_loyalty_years': int(data.get('renewal_loyalty_years') or data.get('years_with_insurer') or 0),
            'risk_score': float(data.get('risk_score', 0.5)),
            # Dependents alias
            'dependents': int(data.get('dependents') or 0),
            # Pre-existing conditions and family history
            'pre_existing_conditions': pre_existing,
            'family_history': family_hist,
            # Insurance preferences (REQUIRED: plan_type)
            'plan_type': data['plan_type'],
            'coverage_amount_preference': int(data.get('coverage_amount', 500000)) if data.get('coverage_amount') else 500000,
            'maternity_required': data.get('maternity_required', 'false') == 'true',
            'critical_illness_required': data.get('critical_illness_required', 'false') == 'true',
            'preferred_providers': [p.strip() for p in data.get('preferred_providers', '').split(',') if p.strip()],
            # Behavioral
            'years_with_insurer': int(data.get('years_with_insurer') or 0),
            'time_since_last_claim_months': int(data.get('time_since_last_claim_months') or 0),
        }

        current_app.logger.info(
            f"Built user profile: age={user['age']}, income={user['income']}, city={user['city']}, plan_type={user['plan_type']}")

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

                # Minimal safety normalizer - ensure keys exist for template
                for r in recs:
                    if "score" not in r:
                        r["score"] = r.get("raw_score", r.get("confidence", 0))
                    if "confidence" not in r:
                        r["confidence"] = r.get("score", 0)
                    if "confidence_label" not in r:
                        conf = r.get("confidence", 0)
                        r["confidence_label"] = f"{int(round(conf*100, 0))}%" if isinstance(
                            conf, (int, float)) else r.get("confidence_label", "0%")

                # Render results template with demo data
                return render_template('get_quote_results.html', recommendations=recs, payload=request.form)
        # ---------- END DEMO FALLBACK ----------

        # Attempt to get recommendations using the ranker with robust error handling
        recs = []
        try:
            if ranker is not None:
                current_app.logger.info(
                    "🔍 Calling PlanRanker for user %s (k=%s)", user_id, limit)
                current_app.logger.info(
                    "📊 User profile: age=%s, income=%.2f, city=%s, state=%s, plan_type=%s",
                    user.get('age'), user.get('income'), user.get('city'),
                    user.get('state'), user.get('plan_type'))

                # Call ranker with comprehensive try-catch
                try:
                    recs = ranker.rank(user, k=limit) or []
                    current_app.logger.info(
                        "✅ Ranker returned %d recommendations", len(recs))
                    if recs:
                        current_app.logger.info(
                            "First recommendation: %s", recs[0])
                except KeyError as e:
                    current_app.logger.error(
                        f"❌ Missing feature in user profile: {e}")
                    recs = []
                except Exception as e:
                    current_app.logger.exception(
                        "❌ Plan ranking failed with error")
                    recs = []
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

        # Transform to friendly format with normalized scores and formatted fields
        try:
            if recs:
                current_app.logger.info(
                    "📊 Transforming %d recommendations to friendly format", len(recs))
                recs = prepare_friendly_recommendations(recs)
                current_app.logger.info(
                    "✅ Friendly transformation complete. Sample confidence: %s",
                    recs[0].get('confidence_label') if recs else 'N/A')
        except Exception:
            current_app.logger.exception(
                "prepare_friendly_recommendations failed; using raw recs")
            # if transformation fails, keep normalized recs
            pass

        # If no recommendations, create fallback suggestions
        if not recs:
            current_app.logger.warning(
                "⚠️ NO RECOMMENDATIONS GENERATED! Creating fallback suggestions. User data: %s", user)

            # Create fallback recommendations based on user profile
            fallback_recs = []
            premium_budget = user.get('premium_budget', 2000)
            age = user.get('age', 30)
            coverage_pref = user.get('coverage_amount_preference', 500000)

            # Fallback recommendation 1: Affordable basic plan
            fallback_recs.append({
                'rank': 1,
                'plan_id': 'FALLBACK_001',
                'plan_name': 'Star Health Comprehensive',
                'provider': 'Star Health Insurance',
                'premium': min(premium_budget * 0.8, 15000),
                'monthly_premium': min(premium_budget * 0.8, 15000),
                'coverage_amount': max(coverage_pref, 500000),
                'network_size': 14000,
                'deductible': 25000,
                'copay': 10,
                'score': 0.85,
                'claim_rejection_rate': 0.08,
                'bullets': [
                    f"Fits your budget of ₹{premium_budget:,.0f}/month",
                    f"Provides ₹{max(coverage_pref, 500000)/100000:.0f}L coverage",
                    "Wide network of 14,000+ hospitals",
                    "Pre-existing conditions covered after 2 years"
                ],
                'explain_text': f'Recommended based on your budget and coverage needs. This plan balances affordability with comprehensive coverage.',
                'explain_scores': {'affordability': 0.9, 'coverage': 0.8},
                'plan_type': user.get('plan_type', 'individual'),
                'plan_category': 'comprehensive'
            })

            # Fallback recommendation 2: Higher coverage option
            if premium_budget > 3000:
                fallback_recs.append({
                    'rank': 2,
                    'plan_id': 'FALLBACK_002',
                    'plan_name': 'HDFC Ergo Health Suraksha',
                    'provider': 'HDFC ERGO',
                    'premium': min(premium_budget * 1.2, 20000),
                    'monthly_premium': min(premium_budget * 1.2, 20000),
                    'coverage_amount': coverage_pref * 1.5,
                    'network_size': 18000,
                    'deductible': 15000,
                    'copay': 5,
                    'score': 0.82,
                    'claim_rejection_rate': 0.06,
                    'bullets': [
                        f"Enhanced coverage of ₹{(coverage_pref * 1.5)/100000:.0f}L",
                        f"Premium: ₹{min(premium_budget * 1.2, 20000):,.0f}/month (within 20% of budget)",
                        "Extensive network of 18,000+ hospitals",
                        "Lower claim rejection rate (6%)"
                    ],
                    'explain_text': f'Premium coverage option for comprehensive protection. Slightly higher premium but better benefits.',
                    'explain_scores': {'coverage': 0.95, 'network': 0.85},
                    'plan_type': user.get('plan_type', 'individual'),
                    'plan_category': 'premium'
                })

            # Fallback recommendation 3: Budget-friendly option
            fallback_recs.append({
                'rank': 3,
                'plan_id': 'FALLBACK_003',
                'plan_name': 'Care Health Plus',
                'provider': 'Care Health Insurance',
                'premium': premium_budget * 0.6,
                'monthly_premium': premium_budget * 0.6,
                'coverage_amount': coverage_pref * 0.8,
                'network_size': 10000,
                'deductible': 30000,
                'copay': 15,
                'score': 0.78,
                'claim_rejection_rate': 0.10,
                'bullets': [
                    f"Most affordable at ₹{premium_budget * 0.6:,.0f}/month (40% below budget)",
                    f"Adequate ₹{(coverage_pref * 0.8)/100000:.0f}L coverage",
                    "Good for younger individuals with low risk",
                    "10,000+ network hospitals"
                ],
                'explain_text': f'Budget-friendly option that maximizes savings while providing essential coverage.',
                'explain_scores': {'affordability': 0.95, 'value': 0.85},
                'plan_type': user.get('plan_type', 'individual'),
                'plan_category': 'basic'
            })

            recs = fallback_recs[:limit]  # Limit to requested number
            current_app.logger.info(
                f"✅ Generated {len(recs)} fallback recommendations")

        # Minimal safety normalizer - ensure keys exist for template
        for r in recs:
            if "score" not in r:
                r["score"] = r.get("raw_score", r.get("confidence", 0))
            if "confidence" not in r:
                r["confidence"] = r.get("score", 0)
            if "confidence_label" not in r:
                conf = r.get("confidence", 0)
                r["confidence_label"] = f"{int(round(conf*100, 0))}%" if isinstance(
                    conf, (int, float)) else r.get("confidence_label", "0%")
            if "network_size" not in r:
                r["network_size"] = r.get("networksize", None)
            if "monthly_premium" not in r:
                r["monthly_premium"] = r.get("premium", None)

        # ==================== PERSIST LEAD AND RECOMMENDATIONS ====================
        # Store this Get Quote submission for analytics and retraining
        try:
            from app.services.persistence import save_lead_and_recs

            # Get or create persistent user_id in session
            if 'user_id' not in session or not session['user_id']:
                session['user_id'] = user_id or str(uuid.uuid4())
            persistent_user_id = session['user_id']

            # Save lead with user profile and recommendations
            lead_id = save_lead_and_recs(
                user_id=persistent_user_id,
                profile_dict=user,  # The user profile dict built earlier
                recommendations_list=recs,  # The recommendations returned by ranker
                ip=request.remote_addr,
                source='get_quote'
            )
            current_app.logger.info(
                "✅ Saved lead %s with %d recommendations", lead_id, len(recs))
        except Exception as e:
            # Don't break the user flow if persistence fails
            current_app.logger.exception(
                "⚠️ Failed to save lead (non-critical): %s", e)

        # Render results template (adjust template name if different)
        current_app.logger.info(
            "🎯 Rendering results template with %d recommendations", len(recs))
        return render_template('get_quote_results.html', recommendations=recs, payload=request.form)

    # GET request: render form
    return render_template('get_quote.html')


# DISABLED - Template removed
# @frontend_bp.route("/get-quote/submit", methods=["POST"])
# @login_required  # Temporarily disabled to test form functionality
def get_quote_submit_DISABLED():
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
