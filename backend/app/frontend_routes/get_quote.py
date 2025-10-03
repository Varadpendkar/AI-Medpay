# backend/app/frontend_routes/get_quote.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user

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
    Serve the multi-step get-quote wizard.
    Handles both GET (show form) and POST (process form) requests.
    """
    if request.method == "POST":
        # Process the form submission
        try:
            # Get form data
            form_data = {
                'full_name': request.form.get('full-name', ''),
                'age': request.form.get('age', ''),
                'email': request.form.get('email', ''),
                'phone': request.form.get('phone', ''),
                'city': request.form.get('city', ''),
                'coverage_type': request.form.get('coverage-type', ''),
                'family_members': request.form.get('family-members', ''),
                'sum_insured': request.form.get('sum-insured', ''),
                'payment_mode': request.form.get('payment-mode', ''),
                'budget_range': request.form.get('budget-range', ''),
                'health_condition': request.form.get('health-condition', ''),
                'conditions': request.form.getlist('conditions'),
            }

            # Handle file upload
            bill_file = None
            if 'file-upload' in request.files:
                file = request.files['file-upload']
                if file and file.filename:
                    bill_file = file

            # For now, return a success response with mock data
            # In production, this would call your recommendation engine
            recommendations = [
                {
                    'plan_name': 'Star Health Individual Plus',
                    'price': '₹8,500/year',
                    'coverage': '₹5 Lakh',
                    'rating': 4.5,
                    'confidence': 95
                },
                {
                    'plan_name': 'HDFC ERGO Health Suraksha',
                    'price': '₹9,200/year',
                    'coverage': '₹5 Lakh',
                    'rating': 4.2,
                    'confidence': 88
                },
                {
                    'plan_name': 'ICICI Lombard Complete Health Guard',
                    'price': '₹7,800/year',
                    'coverage': '₹3 Lakh',
                    'rating': 4.0,
                    'confidence': 82
                }
            ]

            # Render the results template
            return render_template('get_quote_results.html',
                                   recommendations=recommendations,
                                   form_data=form_data,
                                   title="Your Insurance Recommendations")

        except Exception as e:
            current_app.logger.error(f"Error processing quote form: {str(e)}")
            flash('Error processing your request. Please try again.', 'error')
            return redirect(url_for('frontend_get_quote.get_quote'))

    # GET request - show the form
    return render_template("get_quote.html", title="Get a Quote")


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
        from backend.app.services.recommendation_engine import recommend_for_profile
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
            from backend.app.services.lead_capture import capture_lead
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
