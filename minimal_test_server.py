#!/usr/bin/env python3
"""
Minimal Flask server to test if the issue is with our main app
"""

from pathlib import Path
from flask import Flask, render_template
import sys
import os
sys.path.insert(0, '/Users/varadpendkar/Documents/project')
os.environ['PYTHONPATH'] = '/Users/varadpendkar/Documents/project'


# Create minimal Flask app with same configuration
PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_ROOT / 'frontend'

app = Flask(__name__,
            template_folder=str(FRONTEND_DIR / 'templates'),
            static_folder=str(FRONTEND_DIR / 'static'))

# Configure server settings
app.config['SERVER_NAME'] = 'localhost:5002'
app.config['APPLICATION_ROOT'] = '/'
app.config['PREFERRED_URL_SCHEME'] = 'http'


@app.route("/")
def test_home():
    """Simple test home route"""
    print("🏠 Home route called!")
    return render_template("home.html", title="AI-MEDPAY — Test Server")


@app.route("/simple")
def simple_test():
    """Simple route that doesn't use templates"""
    print("✅ Simple route called!")
    return "<h1>Simple Test Route Works!</h1>"


@app.route("/debug")
def debug_info():
    """Debug route to show app info"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(
            f"{rule.rule} -> {rule.endpoint} {list(rule.methods - {'HEAD', 'OPTIONS'})}")

    return f"""
    <h1>Debug Info</h1>
    <h2>Routes:</h2>
    <ul>
    {''.join(f'<li>{route}</li>' for route in routes)}
    </ul>
    <h2>Config:</h2>
    <ul>
    <li>SERVER_NAME: {app.config.get('SERVER_NAME')}</li>
    <li>Template Folder: {app.template_folder}</li>
    <li>Static Folder: {app.static_folder}</li>
    </ul>
    """


if __name__ == '__main__':
    print("🚀 Starting minimal test server on port 5002...")
    print("📍 Test URLs:")
    print("   http://localhost:5002/")
    print("   http://localhost:5002/simple")
    print("   http://localhost:5002/debug")
    app.run(debug=True, port=5002)
