import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


class Config:
    # Secret key for Flask sessions
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key").strip()

    # Database URL (Postgres preferred, fallback to SQLite for dev)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///./dev.db").strip()

    # Disable event system overhead
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Additional common settings
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    # MODEL_PATH = os.getenv("MODEL_PATH", "models/ltr_model.txt")  # Disabled - waiting for new model
    DEBUG = os.getenv("DEBUG", "False").lower() in ("1", "true", "yes")


class DevelopmentConfig(Config):
    DEBUG = True
