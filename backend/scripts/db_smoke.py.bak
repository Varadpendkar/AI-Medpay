import os
import sys
from sqlalchemy import inspect, text
from flask import Flask

# Ensure project root (where app.py and models.py live) is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Load .env from project root (if present)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except Exception:
    pass  # dotenv is optional but recommended

# Import models now that path is set
from models import db, User  # noqa: E402


def create_app():
    app = Flask(__name__)

    # Config from env (fallback provided to avoid RuntimeError)
    db_uri = os.getenv(
        "DATABASE_URL",
        "postgresql://varadpendkar:4321@localhost:5432/aimedpay"  # <- safe fallback
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    return app


def main():
    app = create_app()
    with app.app_context():
        print("✅ Starting DB smoke test...")

        # DB connection check
        try:
            result = db.session.execute(text("SELECT 1")).scalar()
            print("DB connection OK, SELECT 1 returned:", result)
        except Exception as e:
            print("❌ DB connection FAILED:", e)
            return

        # Ensure tables (optional for dev convenience)
        try:
            db.create_all()
        except Exception as e:
            print("⚠️ Could not auto-create tables (this is fine if you use migrations):", e)

        # List tables
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print("📋 Tables in DB:", tables or "None found")

        if not tables:
            print("⚠️ No tables found. Run migrations or ensure create_all() is called in app startup.")
            return

        # Test user
        user = User.query.filter_by(email="test@example.com").first()
        if user:
            print(f"👤 Found test user: id={user.id}, username={user.username}, email={user.email}")
        else:
            print("ℹ️ No test user found. Creating one...")
            u = User(username="test", email="test@example.com")
            u.set_password("password123")
            db.session.add(u)
            db.session.commit()
            print(f"✅ Created test user: id={u.id}")

        # Show users (safe subset)
        users = User.query.all()
        print("👥 Users in DB:", [(u.id, u.username, u.email) for u in users])


if __name__ == "__main__":
    main()

