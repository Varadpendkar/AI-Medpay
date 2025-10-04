#!/usr/bin/env python3
"""Debug the root route specifically"""

from flask import render_template
from backend.app.main import app
import sys
import os
sys.path.insert(0, '/Users/varadpendkar/Documents/project')
os.environ['PYTHONPATH'] = '/Users/varadpendkar/Documents/project'


print("🔍 Debugging Root Route Issue")
print("=" * 40)

# Check template folder configuration
print(f"📁 Template folder: {app.template_folder}")
print(f"📁 Static folder: {app.static_folder}")

# Check if template exists
template_path = os.path.join(app.template_folder, "home.html")
print(f"📄 Template path: {template_path}")
print(f"📄 Template exists: {os.path.exists(template_path)}")

# Test template rendering directly
print("\n🧪 Testing template rendering...")
try:
    with app.app_context():
        result = render_template(
            "home.html", title="AI-MEDPAY — Smart Insurance Recommendations")
        print(f"✅ Template renders successfully (length: {len(result)})")
        has_content = len(result) > 100
        print(f"📝 Has content: {has_content}")
except Exception as e:
    print(f"❌ Template rendering error: {e}")

# Test the function directly
print("\n🧪 Testing route function...")
try:
    with app.app_context():
        from backend.app.main import frontend_home
        result = frontend_home()
        print(f"✅ Route function works (type: {type(result)})")
        if hasattr(result, 'data'):
            print(f"📝 Response length: {len(result.data)}")
except Exception as e:
    print(f"❌ Route function error: {e}")

# Check Flask URL map
print("\n🗺️ Checking URL map...")
for rule in app.url_map.iter_rules():
    if rule.rule == '/':
        print(f"✅ Found root route: {rule.endpoint} -> {rule.methods}")
    elif 'frontend_home' in str(rule.endpoint):
        print(f"🔍 Related route: {rule.endpoint} -> {rule.rule}")

print("\n✨ Debug completed!")
