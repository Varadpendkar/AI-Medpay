# Frontend routes package
from .dashboard import frontend_bp as dashboard_bp
from .get_quote import frontend_bp as get_quote_bp
from .bill_buster import frontend_bp as bill_buster_bp
from .resources import resources_bp


def register_blueprints(app):
    """Register all frontend route blueprints"""
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(get_quote_bp)
    app.register_blueprint(bill_buster_bp)
    app.register_blueprint(resources_bp)
