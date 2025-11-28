from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    # ⬇️ widened from 128 → 255 to support longer hashes (scrypt/argon2)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    policies = db.relationship("InsurancePolicy", backref="user", lazy=True)
    bills = db.relationship("MedicalBill", backref="user", lazy=True)

    def set_password(self, password):
        """Hashes the password and stores it"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks the password against the stored hash"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}, Email: {self.email}>"


class InsurancePolicy(db.Model):
    __tablename__ = "insurance_policies"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    provider = db.Column(db.String(100), nullable=False)
    coverage_type = db.Column(db.String(100), nullable=False)
    premium = db.Column(db.Float, nullable=False)
    deductible = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<InsurancePolicy {self.provider}, Coverage: {self.coverage_type}, "
            f"Premium: {self.premium}, Deductible: {self.deductible}>"
        )


class MedicalBill(db.Model):
    __tablename__ = "medical_bills"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    provider = db.Column(db.String(100), nullable=False)
    service_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default="unpaid")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<MedicalBill Provider: {self.provider}, "
            f"Date: {self.service_date}, Amount: {self.amount}, Status: {self.status}>"
        )
