#!/usr/bin/env python3
"""Remove specified @app.route functions from app.py and append new router placeholders.
WARNING: This edits project/app.py in-place. Make sure your backup is available.
"""
import ast
import sys
from pathlib import Path

APP_PY = Path("app.py")
if not APP_PY.exists():
    print("Error: app.py not found. Adjust path if necessary.")
    sys.exit(1)

# routes to remove (exact strings)
ROUTES_TO_REMOVE = {
    "/", "/login", "/register", "/dashboard", "/recommendation", "/recommendations",
    "/compare", "/bill-buster", "/bill_buster", "/resources"
}

src = APP_PY.read_text(encoding="utf-8")
tree = ast.parse(src)


class RouteRemover(ast.NodeTransformer):
    def _decorator_targets_route(self, dec):
        # checks if decorator is @app.route("/path") or @app.route('/path', methods=['GET'])
        # returns the route path string if found, else None
        if isinstance(dec, ast.Call):
            func = dec.func
            if isinstance(func, ast.Attribute) and getattr(func.value, "id", None) in ("app",):
                if func.attr == "route":
                    # first positional arg often the route string
                    if dec.args and isinstance(dec.args[0], (ast.Constant, ast.Str)):
                        return dec.args[0].s if isinstance(dec.args[0], ast.Str) else dec.args[0].value
        return None

    def visit_FunctionDef(self, node):
        # inspect decorators
        for dec in node.decorator_list:
            path = self._decorator_targets_route(dec)
            if path and path in ROUTES_TO_REMOVE:
                # remove this function by returning None
                print(
                    f"Removing route handler for: {path} (function {node.name})")
                return None
        return node


new_tree = RouteRemover().visit(tree)
ast.fix_missing_locations(new_tree)

try:
    new_src = ast.unparse(new_tree)  # Python 3.9+
except Exception:
    try:
        import astor
        new_src = astor.to_source(new_tree)
    except Exception as e:
        print("ERROR: Could not unparse AST. Install astor or use Python 3.9+.")
        raise

# append a new router block (placeholders)
placeholder = '''

# -------------------------------
# NEW FRONTEND ROUTES (PLACEHOLDERS)
# These routes are minimal placeholders for the new Jinja/Tailwind frontend.
# Replace template names with actual templates when scaffolding the new frontend.
# -------------------------------

from flask import render_template

@app.route("/")
def frontend_home():
    # placeholder - render new home template
    return render_template("home.html", title="Home")

@app.route("/login", methods=["GET", "POST"])
def frontend_login():
    # placeholder - render new login page (Flask-WTF forms expected)
    return render_template("login.html", title="Login")

@app.route("/register", methods=["GET", "POST"])
def frontend_register():
    return render_template("register.html", title="Register")

@app.route("/dashboard")
def frontend_dashboard():
    # login_required should already be handled in backend; keep existing decorators if required.
    return render_template("dashboard.html", title="Dashboard")

@app.route("/recommendation")
def frontend_recommendation():
    return render_template("recommendation.html", title="Recommendation")

@app.route("/compare")
def frontend_compare():
    return render_template("compare.html", title="Compare")

@app.route("/bill-buster", methods=["GET", "POST"])
def frontend_bill_buster():
    return render_template("bill_buster.html", title="Bill Buster")

@app.route("/resources")
def frontend_resources():
    return render_template("resources.html", title="Resources")
'''

# Write back the modified app.py
APP_PY.write_text(new_src + "\n" + placeholder, encoding="utf-8")
print("Edited app.py: removed specified page route handlers and appended placeholder router block.")
