from app.frontend_routes.dashboard import frontend_bp
from app.frontend_routes.get_quote import frontend_bp as get_quote_bp
from app.frontend_routes.bill_buster import frontend_bp as bill_buster_bp
from app.frontend_routes.resources import resources_bp
import os
import logging
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session, send_from_directory, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from urllib.parse import urlencode as url_encode
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from flask_migrate import Migrate
from pathlib import Path
from app.utils.simple_ranker import PlanRanker
import pandas as pd
from datetime import datetime
from app.services.bill_analyzer import parse_bill_file
from app.services.negotiation_engine import analyze_parsed_items
import app.services.platform_integrator as integrator
from urllib.parse import urlparse, urljoin
from app.models.models import db, User
from app.core.forms import RegisterForm, LoginForm, CompareForm
from app.core.config import DevelopmentConfig

# Configure Flask to use frontend folder for templates and static files
PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_ROOT.parent.parent / 'frontend'
app = Flask(__name__,
            template_folder=str(FRONTEND_DIR / 'templates'),
            static_folder=str(FRONTEND_DIR / 'static'))

# Configure server settings to fix URL building issues
# Note: SERVER_NAME can cause routing issues, so we'll handle url_for differently
app.config['APPLICATION_ROOT'] = '/'
app.config['PREFERRED_URL_SCHEME'] = 'http'

logging.basicConfig(level=logging.INFO)

RANKER_MODEL_PATH = os.environ.get('RANKER_MODEL_PATH') or str(
    PROJECT_ROOT / 'models' / 'ltr_model.txt')
try:
    ranker = PlanRanker(PROJECT_ROOT)
    logging.info("✅ PlanRanker initialized successfully (path=%s)",
                 RANKER_MODEL_PATH)
except FileNotFoundError as e:
    logging.warning("⚠️ PlanRanker not available: %s", e)
    ranker = None
app.config.from_object(DevelopmentConfig)
BASE_DIR = os.path.dirname(__file__)
app.config.setdefault('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'uploads'))
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db.init_app(app)

# Template context processor to handle url_for safely


@app.context_processor
def inject_safe_url_for():
    """Provide a safe url_for function for templates"""
    def safe_url_for(endpoint, **values):
        try:
            from flask import url_for
            return url_for(endpoint, **values)
        except Exception:
            # Fallback for static files and common routes
            if endpoint == 'static':
                filename = values.get('filename', '')
                return f"/static/{filename}"
            elif endpoint == 'frontend_home':
                return "/"
            elif endpoint == 'frontend_get_quote.get_quote':
                return "/get-quote"
            else:
                return f"/{endpoint.replace('_', '-')}"
    return dict(url_for=safe_url_for)


migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'frontend_login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# --- OAuth Configuration ---
oauth = OAuth()
# Ensure these environment vars are set by deployer
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    access_token_url='https://oauth2.googleapis.com/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://www.googleapis.com/oauth2/v3/userinfo',
    client_kwargs={'scope': 'openid email profile'},
)
oauth.init_app(app)

# Register frontend routes blueprints
app.register_blueprint(frontend_bp)
app.register_blueprint(get_quote_bp)
app.register_blueprint(bill_buster_bp)
app.register_blueprint(resources_bp)

# Safe fallback routes to ensure login/register always work


@app.route("/auth/web/login", methods=["GET", "POST"])
@app.route("/login-safe", methods=["GET", "POST"])
def safe_login():
    try:
        form = LoginForm()
        if form.validate_on_submit():
            flash("Demo login attempt - redirecting to dashboard", "info")
            return redirect(url_for('index'))
        return render_template("login.html", title="Login", form=form)
    except Exception as e:
        return f"<h1>Login Page</h1><p>Form error: {e}</p><p><a href='/'>Home</a></p>", 200


@app.route("/auth/web/register", methods=["GET", "POST"])
@app.route("/register-safe", methods=["GET", "POST"])
def safe_register():
    try:
        form = RegisterForm()
        if form.validate_on_submit():
            flash("Demo registration attempt - redirecting to dashboard", "info")
            return redirect(url_for('index'))
        return render_template("register.html", title="Register", form=form)
    except Exception as e:
        return f"<h1>Register Page</h1><p>Form error: {e}</p><p><a href='/'>Home</a></p>", 200


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def is_safe_next(target):
    ref = urlparse(request.host_url)
    test = urlparse(urljoin(request.host_url, target or ''))
    return test.scheme in ('http', 'https') and test.netloc == ref.netloc


def normalize_plan_record(rec):
    """Normalize common plan dict aliases so downstream code can rely on plan_id/plan_name/provider.
    Also maps common numeric fields where possible.
    """
    if not isinstance(rec, dict):
        return rec
    if 'plan_id' not in rec:
        for k in ('planid', 'id', 'planId', 'plan'):
            if k in rec and rec.get(k) not in (None, ''):
                rec['plan_id'] = rec[k]
                break
    if 'plan_name' not in rec:
        for k in ('planname', 'name', 'policy_name'):
            if k in rec and rec.get(k):
                rec['plan_name'] = rec[k]
                break
    if 'provider' not in rec:
        for k in ('insurer', 'company'):
            if k in rec and rec.get(k):
                rec['provider'] = rec[k]
                break
    if 'network_size' not in rec:
        for k in ('networksize', 'networkSize'):
            if k in rec and rec.get(k) not in (None, ''):
                rec['network_size'] = rec[k]
                break
    if 'coverage_amount' not in rec:
        for k in ('coverageamount', 'coverageAmount'):
            if k in rec and rec.get(k) not in (None, ''):
                rec['coverage_amount'] = rec[k]
                break
    if 'claim_rejection_rate' not in rec:
        for k in ('claimrejectionrate',):
            if k in rec and rec.get(k) not in (None, ''):
                rec['claim_rejection_rate'] = rec[k]
                break
    return rec


def safe_num(rec, *keys, default=None):
    """Return first parsable numeric value for given keys from a dict, else default."""
    if not isinstance(rec, dict):
        return default
    for k in keys:
        if k in rec and rec[k] not in (None, '', 'NA'):
            try:
                v = rec[k]
                if isinstance(v, (int, float)):
                    return v
                s = str(v).replace(',', '').strip()
                if s == '':
                    continue
                return float(s) if '.' in s else int(float(s))
            except Exception:
                continue
    return default


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))


def _load_user_profile(user_id):
    """Load a demo user profile from data/users.csv, falling back to sensible defaults.
    Accepts both raw IDs like 'U0001' and numeric like '1'.
    """
    users_csv = PROJECT_ROOT / 'data' / 'users.csv'
    try:
        df = pd.read_csv(users_csv)
        uid = str(user_id)
        row = None
        if 'user_id' in df.columns:
            r = df[df['user_id'].astype(str) == uid]
            if not r.empty:
                row = r.iloc[0]
            elif uid.isdigit():
                z = f'U{int(uid):04d}'
                r = df[df['user_id'].astype(str) == z]
                if not r.empty:
                    row = r.iloc[0]
        if row is not None:
            return {'user_id': uid, 'age': int(row.get('age', 35) or 35), 'income': float(row.get('income', 600000) or 600000), 'dependents': int(row.get('dependents', 0) or 0), 'health_status': str(row.get('health_status', 'good') or 'good').lower(), 'coverage_preference': str(row.get('coverage_preference', 'balanced') or 'balanced').lower(), 'preferred_providers': str(row.get('preferred_providers', '') or ''), 'risk_score': float(row.get('risk_score', 0.2) or 0.2), 'past_claims_count': int(row.get('past_claims_count', 0) or 0), 'past_claims_amount': float(row.get('past_claims_amount', 0.0) or 0.0), 'state': str(row.get('state', 'Maharashtra') or 'Maharashtra'), 'target_coverage': 0, 'max_premium': 0}
    except Exception:
        pass
    return {'user_id': str(user_id), 'age': 35, 'income': 600000, 'dependents': 0, 'health_status': 'good', 'coverage_preference': 'balanced', 'preferred_providers': '', 'risk_score': 0.2, 'past_claims_count': 0, 'past_claims_amount': 0.0, 'state': 'Maharashtra', 'target_coverage': 0, 'max_premium': 0}


@app.route('/api/recommendations', methods=['GET'])
def api_recommendations():
    user_id = request.args.get('user_id') or request.args.get(
        'uid') or request.headers.get('X-User-Id')
    if not user_id:
        return (jsonify({'error': 'user_id required'}), 400)
    try:
        limit = int(request.args.get('limit', 5))
    except Exception:
        limit = 5
    variant = request.args.get('variant', 'hybrid')
    user = _load_user_profile(user_id)
    try:
        if ranker is None:
            app.logger.warning(
                'Ranker not available - using fallback recommendations')
            recs = []
        else:
            recs = ranker.rank(user, k=limit)
    except Exception as e:
        app.logger.error('Ranker failed: %s', e)
        recs = []
    if not recs:
        try:
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
                    pass
                recs = []
                for i, r in enumerate(df.itertuples(index=False), start=1):
                    recs.append({'plan_id': getattr(r, 'plan_id', None), 'provider': getattr(r, 'provider', None) if hasattr(r, 'provider') else None, 'plan_name': getattr(r, 'plan_name', None) if hasattr(r, 'plan_name') else getattr(r, 'plan_id', None), 'monthly_premium': float(getattr(r, 'premium', getattr(
                        r, 'monthly_premium', 0.0)) or 0.0), 'deductible': float(getattr(r, 'deductible', 0.0) or 0.0), 'network_size': int(getattr(r, 'network_size', 0) or 0), 'score': float(getattr(r, 'score', 0.0) or 0.0), 'rank': i, 'explain_text': 'Sample ranking fallback.', 'explain_scores': {'sample_score': float(getattr(r, 'score', 0.0) or 0.0)}})
        except Exception as e:
            app.logger.error('Sample fallback failed: %s', e)
            recs = []

    def _format_rec(r, idx):
        mp = r.get('premium') if isinstance(r, dict) else None
        bullets = r.get('bullets', []) if isinstance(r, dict) else []
        explain_text = r.get('explain_text') or (' '.join(
            bullets) if bullets else 'Low premium and large network contributed to this rank.')
        explain_scores = r.get('explain_scores') or {'premium_income_ratio': float(r.get(
            'premium_income_ratio', 0.0) or 0.0), 'provider_match': int(r.get('provider_match', 0) or 0)}
        return {'plan_id': r.get('plan_id'), 'provider': r.get('provider'), 'plan_name': r.get('plan_name') or r.get('plan_id'), 'monthly_premium': float(mp) if mp is not None else float(r.get('monthly_premium', 0.0) or 0.0), 'deductible': float(r.get('deductible', 0.0) or 0.0), 'network_size': int(r.get('network_size', 0) or 0), 'score': float(r.get('score', 0.0) or 0.0), 'rank': idx, 'explain_text': explain_text, 'explain_scores': explain_scores, 'explain_top_features': r.get('explain_top_features') or []}
    if recs and isinstance(recs[0], dict) and ('bullets' in recs[0]):
        formatted = [_format_rec(r, i)
                     for i, r in enumerate(recs[:limit], start=1)]
        model_version = 'ltr_model_txt'
    else:
        formatted = recs[:limit]
        model_version = 'sample_or_heuristic'
    payload = {'user_id': str(user_id), 'model_version': model_version, 'timestamp': datetime.utcnow(
    ).isoformat() + 'Z', 'recommendations': formatted}
    return jsonify(payload)


@app.route('/api/bill/parse', methods=['POST'])
def api_bill_parse():
    ctype = request.content_type or ''
    if ctype.startswith('multipart/form-data'):
        f = request.files.get('file')
        if not f:
            return (jsonify({'status': 'error', 'message': 'file field missing'}), 400)
        tcmd = app.config.get(
            'TESSERACT_CMD') if 'TESSERACT_CMD' in app.config else None
        result = parse_bill_file(file_storage=f, tesseract_cmd=tcmd)
        return jsonify(result)
    else:
        j = request.get_json(force=True, silent=True) or {}
        text = j.get('text')
        if not text:
            return (jsonify({'status': 'error', 'message': 'text payload missing'}), 400)
        result = parse_bill_file(text=text)
        return jsonify(result)


@app.route('/api/bill/analyze', methods=['POST'])
def api_bill_analyze():
    j = request.get_json(force=True, silent=True) or {}
    parsed_items = j.get('parsed_items')
    if parsed_items is None:
        return (jsonify({'status': 'error', 'message': 'parsed_items required'}), 400)
    user = None
    user_id = j.get('user_id')
    if user_id:
        try:
            users_csv = PROJECT_ROOT / 'data' / 'users.csv'
            df = pd.read_csv(users_csv)
            r = df[df['user_id'].astype(str) == str(user_id)]
            if not r.empty:
                u = r.iloc[0].to_dict()
                user = {'user_id': u.get('user_id'), 'age': u.get(
                    'age'), 'risk_score': u.get('risk_score')}
        except Exception:
            user = {'user_id': user_id}
    plan_id = j.get('plan_id')
    result = analyze_parsed_items(parsed_items, user=user, plan_id=plan_id)
    return jsonify({'status': 'ok', **result})


@app.route('/api/platforms', methods=['GET'])
def api_platforms():
    plats = integrator.list_platforms()
    return jsonify({'status': 'ok', 'platforms': plats})


@app.route('/api/platforms/plans', methods=['GET'])
def api_platforms_plans():
    source = request.args.get('source', 'internal')
    limit = request.args.get('limit')
    try:
        limit_int = int(limit) if limit is not None else None
    except Exception:
        limit_int = None
    plans = integrator.get_plans(source=source, limit=limit_int)
    return jsonify({'status': 'ok', 'source': source, 'plans': plans})


@app.route('/api/plan/<plan_id>', methods=['GET'])
def api_plan_detail(plan_id):
    plan = integrator.get_plan_by_id(plan_id)
    if not plan:
        return (jsonify({'status': 'error', 'message': 'plan not found'}), 404)
    return jsonify({'status': 'ok', 'plan': plan})


# --- Guaranteed root route fallback (safe & idempotent) ---
@app.route("/", methods=["GET"])
def __guaranteed_index():
    """Fallback index: try to render 'home.html' from current template folder,
    otherwise return a small friendly HTML so / never returns 404 in dev.
    """
    try:
        # Prefer the app's template if present
        return render_template("home.html")
    except Exception as e:
        app.logger.warning(
            "Fallback index: home.html not found or render failed: %s", e)
        return (
            "<!doctype html><html><head><meta charset='utf-8'><title>Home</title></head>"
            "<body style='font-family:system-ui,Segoe UI,Roboto,-apple-system,Arial;margin:40px'>"
            "<h1>Welcome — Home page (fallback)</h1>"
            "<p>Your <code>home.html</code> template could not be rendered. Check template path.</p>"
            "<p><a href='/get-quote'>Go to Get a Quote</a></p>"
            "</body></html>"
        )


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("🚀 Starting Flask server on http://127.0.0.1:5001")
    app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)


# -------------------------------
# NEW FRONTEND ROUTES (PLACEHOLDERS)
# These routes are minimal placeholders for the new Jinja/Tailwind frontend.
# Replace template names with actual templates when scaffolding the new frontend.
# -------------------------------

# --- GOOGLE OAUTH ROUTES ---

@app.route("/auth/google")
def auth_google():
    next_url = request.args.get(
        'next') or request.referrer or url_for('index')
    # state can carry 'next' so we return properly after callback
    redirect_uri = url_for('auth_google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri, state=url_encode({'next': next_url}))


@app.route("/auth/google/callback")
def auth_google_callback():
    token = oauth.google.authorize_access_token()
    if not token:
        flash("Google sign-in failed.", "error")
        return redirect(url_for('frontend.login'))

    userinfo = oauth.google.parse_id_token(
        token) or oauth.google.get('userinfo').json()

    # userinfo contains email, name, picture, sub
    email = userinfo.get('email')
    name = userinfo.get('name') or ''
    google_id = userinfo.get('sub')

    # Integrate with existing user model & login logic
    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            # Create user using existing model structure
            # Use email as username and name as display name
            username = email.split('@')[0]  # Use part before @ as username
            counter = 1
            original_username = username
            # Ensure username is unique
            while User.query.filter_by(username=username).first():
                username = f"{original_username}{counter}"
                counter += 1

            user = User(
                username=username,
                email=email
            )
            # Set a random password for Google users
            user.set_password(os.urandom(24).hex())
            db.session.add(user)
            db.session.commit()

        # Login the user using existing login mechanism
        login_user(user)
        flash("Successfully signed in with Google!", "success")

    except Exception as e:
        app.logger.error(f"Google OAuth error: {e}")
        flash("Sign-in failed. Please try again.", "error")
        return redirect(url_for('frontend.register'))

    # Redirect to next URL
    state = request.args.get('state')
    if state:
        try:
            decoded = dict([kv.split('=') for kv in state.split('&')])
            next_url = decoded.get('next') or url_for('frontend.dashboard')
        except Exception:
            next_url = url_for('frontend.dashboard')
    else:
        next_url = url_for('frontend.dashboard')

    return redirect(next_url)


@app.route("/auth/login", methods=["POST"])
def auth_login():
    """API endpoint for form-based login"""
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        remember = form.remember.data

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            return redirect(url_for('frontend.dashboard'))
        else:
            flash('Invalid email or password', 'error')

    return redirect(url_for('frontend.login'))


@app.route("/auth/register", methods=["POST"])
def auth_register():
    """API endpoint for form-based registration"""
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('frontend.register'))

        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return redirect(url_for('frontend.register'))

        user = User(
            username=username,
            email=email
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash('Registration successful!', 'success')
        return redirect(url_for('frontend.dashboard'))

    flash('Registration failed. Please check your information.', 'error')
    return redirect(url_for('frontend.register'))


# --- FRONTEND ROUTES (Home) ---

@app.route("/")
def index():
    """Root route - render marketing/homepage template if present, else return fallback HTML."""
    app.logger.info("🏠 Root route called - rendering home page")
    try:
        # try frontend template location first (project frontend)
        return render_template('home.html')
    except Exception as e:
        app.logger.warning(f"⚠️ Could not render home.html: {e}")
        # fallback minimal page when template missing
        return (
            "<!doctype html><html><head><meta charset='utf-8'><title>Home</title></head>"
            "<body style='font-family:system-ui,Segoe UI,Roboto,-apple-system,Arial;margin:40px'>"
            "<h1>Welcome — Home page</h1>"
            "<p>The homepage template is not found. Create <code>frontend/templates/home.html</code> or "
            "place your marketing HTML there.</p>"
            "<p><a href='/get-quote'>Go to Get a Quote</a></p>"
            "</body></html>"
        )


@app.route("/favicon.ico")
def favicon():
    """Serve favicon to stop 404 requests"""
    # Try multiple possible locations for favicon
    static_dirs = [
        os.path.join(app.static_folder, "images"),
        os.path.join(app.static_folder),
        os.path.join(os.path.dirname(__file__), "..",
                     "..", "frontend", "static", "images"),
        os.path.join(os.path.dirname(__file__), "..",
                     "..", "frontend", "static")
    ]

    for static_dir in static_dirs:
        static_dir = os.path.abspath(static_dir)
        favicon_path = os.path.join(static_dir, "favicon.ico")
        if os.path.exists(favicon_path):
            return send_from_directory(static_dir, "favicon.ico")

    # If no favicon found, return a simple 1x1 transparent PNG
    from flask import Response
    # Minimal 1x1 transparent PNG in base64
    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x18\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82'
    return Response(png_data, mimetype='image/png')


@app.route('/_dev/endpoints')
def _dev_list_endpoints():
    if not app.debug:
        return jsonify(error="not allowed"), 403
    return jsonify(sorted([f"{r.endpoint} {r.rule}" for r in current_app.url_map.iter_rules()]))


@app.route("/debug-routes")
def debug_routes():
    """Debug route to show all registered routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'rule': rule.rule,
            'endpoint': rule.endpoint,
            'methods': list(rule.methods - {'HEAD', 'OPTIONS'})
        })
    routes.sort(key=lambda x: x['rule'])

    html = "<h1>Debug: All Registered Routes</h1><ul>"
    for route in routes:
        html += f"<li><b>{route['rule']}</b> -> {route['endpoint']} {route['methods']}</li>"
    html += "</ul>"
    html += "<p><a href='/'>Test Home Route</a></p>"
    return html


# Old frontend_login and frontend_register functions removed - replaced with proper route handlers below


# Dashboard route moved to frontend_routes blueprint

# Proper auth route handlers that render templates and handle forms
@app.route("/login", methods=["GET", "POST"])
def login():
    # if user already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for("frontend.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data
        # Find user by email
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=form.remember.data)
            flash("Logged in successfully.", "success")
            next_page = request.args.get(
                "next") or url_for("frontend.dashboard")
            return redirect(next_page)
        else:
            flash("Invalid credentials. Please try again.", "danger")

    return render_template("login.html", title="Log in", form=form)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("frontend.dashboard"))

    form = RegisterForm()
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter_by(
            email=form.email.data.strip().lower()).first()
        if existing_user:
            flash("Email already registered. Please log in instead.", "danger")
            return redirect(url_for("login"))

        existing_username = User.query.filter_by(
            username=form.username.data.strip()).first()
        if existing_username:
            flash("Username already taken. Please choose another.", "danger")
            return render_template("register.html", title="Register", form=form)

        # Create new user
        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", title="Register", form=form)


# Debug route to test if routes are being registered
@app.route("/test-routes")
def test_routes():
    return "Routes are working! Login and register should work now."


@app.route("/recommendation")
def frontend_recommendation():
    return render_template("recommendation.html", title="Recommendation")


@app.route("/compare")
def frontend_compare():
    return render_template("compare.html", title="Compare")


# Bill Buster route moved to frontend_routes blueprint


# Resources route moved to blueprint
