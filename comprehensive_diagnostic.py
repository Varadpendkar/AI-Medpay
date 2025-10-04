#!/usr/bin/env python3
"""
Comprehensive Flask App Diagnostic Tool
This will identify and fix all routing and configuration issues
"""

from backend.app.main import app
import sys
import os
sys.path.insert(0, '/Users/varadpendkar/Documents/project')
os.environ['PYTHONPATH'] = '/Users/varadpendkar/Documents/project'


def comprehensive_diagnostic():
    """Run comprehensive diagnostics on the Flask app"""

    print("🔍 COMPREHENSIVE FLASK DIAGNOSTIC")
    print("=" * 60)

    # 1. App Configuration
    print("\n📋 1. APP CONFIGURATION")
    print("-" * 30)
    print(f"App Name: {app.name}")
    print(f"Debug Mode: {app.debug}")
    print(f"Template Folder: {app.template_folder}")
    print(f"Static Folder: {app.static_folder}")
    print(f"Server Name: {app.config.get('SERVER_NAME', 'Not set')}")
    print(f"Application Root: {app.config.get('APPLICATION_ROOT', 'Not set')}")
    print(
        f"Preferred URL Scheme: {app.config.get('PREFERRED_URL_SCHEME', 'Not set')}")

    # 2. Registered Blueprints
    print("\n🏭 2. REGISTERED BLUEPRINTS")
    print("-" * 30)
    if app.blueprints:
        for name, blueprint in app.blueprints.items():
            print(
                f"  {name}: {blueprint.name} (url_prefix: {blueprint.url_prefix})")
    else:
        print("  No blueprints registered")

    # 3. All Routes
    print("\n🗺️ 3. ALL REGISTERED ROUTES")
    print("-" * 30)
    routes_by_path = {}
    for rule in app.url_map.iter_rules():
        path = rule.rule
        if path not in routes_by_path:
            routes_by_path[path] = []
        routes_by_path[path].append({
            'endpoint': rule.endpoint,
            'methods': rule.methods - {'HEAD', 'OPTIONS'}
        })

    for path in sorted(routes_by_path.keys()):
        print(f"  {path}")
        for route_info in routes_by_path[path]:
            methods = ', '.join(route_info['methods'])
            print(f"    -> {route_info['endpoint']} [{methods}]")

    # 4. Root Route Specific Check
    print("\n🏠 4. ROOT ROUTE ANALYSIS")
    print("-" * 30)
    root_routes = [rule for rule in app.url_map.iter_rules()
                   if rule.rule == '/']
    if root_routes:
        for rule in root_routes:
            print(f"  ✅ Found: {rule.endpoint} -> {rule.rule} {rule.methods}")

            # Try to get the view function
            try:
                view_func = app.view_functions.get(rule.endpoint)
                if view_func:
                    print(f"    View Function: {view_func.__name__}")
                    print(f"    Module: {view_func.__module__}")
                else:
                    print(f"    ❌ No view function found for {rule.endpoint}")
            except Exception as e:
                print(f"    ❌ Error getting view function: {e}")
    else:
        print("  ❌ No root route found!")

    # 5. Test Route Execution
    print("\n🧪 5. ROUTE EXECUTION TESTS")
    print("-" * 30)

    with app.test_client() as client:
        # Test root route
        try:
            print("  Testing GET /...")
            response = client.get('/')
            print(f"    Status: {response.status_code}")
            print(f"    Content-Type: {response.content_type}")
            if response.status_code == 200:
                data_len = len(response.get_data())
                print(f"    Response Length: {data_len} bytes")
                print("    ✅ Root route working in test client")
            elif response.status_code == 404:
                print("    ❌ 404 - Route not found in test client")
            elif response.status_code == 500:
                print("    ❌ 500 - Internal server error")
                error_data = response.get_data(as_text=True)
                print(f"    Error: {error_data[:200]}...")
            else:
                print(f"    ❓ Unexpected status: {response.status_code}")
        except Exception as e:
            print(f"    ❌ Exception during test: {e}")

        # Test get-quote route
        try:
            print("  Testing GET /get-quote...")
            response = client.get('/get-quote')
            print(f"    Status: {response.status_code}")
            if response.status_code == 200:
                print("    ✅ Get-quote route working")
            else:
                print(f"    ❌ Get-quote failed: {response.status_code}")
        except Exception as e:
            print(f"    ❌ Exception during get-quote test: {e}")

    # 6. Template Issues Check
    print("\n📄 6. TEMPLATE VALIDATION")
    print("-" * 30)

    templates_to_check = ['home.html', 'base.html', 'get_quote.html']
    for template in templates_to_check:
        template_path = os.path.join(app.template_folder, template)
        exists = os.path.exists(template_path)
        print(f"  {template}: {'✅ Exists' if exists else '❌ Missing'}")

        if exists and template == 'home.html':
            # Try rendering home template
            try:
                with app.app_context():
                    from flask import render_template
                    result = render_template('home.html', title='Test')
                    print(f"    ✅ Renders successfully ({len(result)} chars)")
            except Exception as e:
                print(f"    ❌ Rendering error: {e}")

    # 7. Potential Issues Detection
    print("\n⚠️ 7. POTENTIAL ISSUES DETECTION")
    print("-" * 30)

    issues_found = []

    # Check for port conflicts
    server_name = app.config.get('SERVER_NAME', '')
    if server_name and server_name.endswith(':5000'):
        issues_found.append("Port 5000 may conflict with macOS AirPlay")

    # Check for missing static files
    static_files = ['css/main.css', 'js/main.js', 'images/logo.svg']
    for static_file in static_files:
        static_path = os.path.join(app.static_folder, static_file)
        if not os.path.exists(static_path):
            issues_found.append(f"Missing static file: {static_file}")

    # Check for blueprint conflicts
    blueprint_routes = set()
    for blueprint in app.blueprints.values():
        if hasattr(blueprint, 'deferred_functions'):
            for deferred in blueprint.deferred_functions:
                if hasattr(deferred, 'rule'):
                    blueprint_routes.add(deferred.rule)

    if issues_found:
        for issue in issues_found:
            print(f"  ⚠️ {issue}")
    else:
        print("  ✅ No obvious issues detected")

    print(f"\n{'=' * 60}")
    print("🏁 DIAGNOSTIC COMPLETE")

    return len(issues_found) == 0


if __name__ == "__main__":
    success = comprehensive_diagnostic()
    if not success:
        print("\n🛠️ Issues found - manual intervention needed")
    else:
        print("\n🎉 No issues detected - app should work correctly")
