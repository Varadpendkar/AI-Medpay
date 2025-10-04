#!/usr/bin/env python3
"""
Minimal working Flask app to test basic functionality
This will help us isolate the issue
"""

from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    print("🏠 MINIMAL HOME ROUTE CALLED!")
    return """
    <h1>🏥 AI-MEDPAY - Minimal Test</h1>
    <p>If you can see this, the basic Flask app works!</p>
    <ul>
        <li><a href="/test">Test Route</a></li>
        <li><a href="/get-quote">Get Quote (should work)</a></li>
    </ul>
    """


@app.route("/test")
def test():
    print("🧪 TEST ROUTE CALLED!")
    return "<h1>Test Route Works!</h1><a href='/'>Back to Home</a>"


if __name__ == '__main__':
    print("🚀 Starting minimal Flask app on port 8080...")
    app.run(debug=True, host='0.0.0.0', port=8080)
