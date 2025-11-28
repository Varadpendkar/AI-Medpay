#!/usr/bin/env python3
"""
Setup User 1 Profile with Recommendations from Lead Data

This script:
1. Creates/updates User 1 with email user1@aimedpay.com
2. Links the user to their saved lead data (recommendations)
3. Creates a user profile table to store extended profile information
"""
import sqlite3
import json
import os
import sys

# Prevent Flask app from running when importing
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import just the database and models, not the main app
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.models.models import User
from app.core.config import DevelopmentConfig

# Create minimal Flask app for database operations
app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

# Import db after app config
from app.models.models import db
db.init_app(app)

# User 1 profile data from the screen recording
USER1_PROFILE = {
    "email": "user1@aimedpay.com",
    "username": "user1",
    "password": "user1password",  # Change this to a secure password
    
    # Profile details from form
    "age": 21,
    "gender": "male",
    "annual_income": 1200000,
    "marital_status": "single",
    "city": "Pune",
    "state": "Maharashtra",
    "region": "Wagholi",
    "occupation_type": "salaried",
    "plan_type": "individual",
    
    # Plan needs
    "coverage_amount": 2000000,  # 20L
    "payment_mode": "monthly",
    "existing_policy": False,
    "premium_budget": 10000,
    
    # Health & History
    "smoking_flag": False,
    "has_diabetes": True,
    "has_hypertension": True,
    "has_obesity": True,
    "has_heart_disease": False,
    "has_cancer_history": False,
    "claim_history_count": 3,
    "renewal_loyalty_years": 3,
    "urban_rural": "urban",
    "dependents": 0
}

# Expected recommendations from the screen recording
EXPECTED_RECOMMENDATIONS = [
    {
        "rank": 1,
        "plan_id": "PL10094",
        "plan_name": "Senior Citizen Health Bronze",
        "provider": "Cholamandalam MS General Insurance",
        "premium": 1100,
        "monthly_premium": 100,
        "deductible": 20000,
        "network_size": 68,
        "coverage_amount": 225640,
        "explanation": "Highly affordable at 1.1% of annual income. Good network of 68 hospitals. Excellent value: ₹505 coverage per ₹1 premium."
    },
    {
        "rank": 2,
        "plan_id": "PL10095",
        "plan_name": "Senior Citizen Health Bronze",
        "provider": "Magma General Insurance",
        "premium": 1100,
        "monthly_premium": 100,
        "deductible": 20000,
        "network_size": 22,
        "coverage_amount": 223340,
        "explanation": "Highly affordable at 1.1% of annual income. Excellent value: ₹203 coverage per ₹1 premium. Reliable coverage you can trust."
    },
    {
        "rank": 3,
        "plan_id": "PL10096",
        "plan_name": "Senior Citizen Health Bronze",
        "provider": "Bandhan General Insurance",
        "premium": 1200,
        "monthly_premium": 100,
        "deductible": 10000,
        "network_size": 45,
        "coverage_amount": 243600,
        "explanation": "Highly affordable at 1.2% of annual income. Excellent value: ₹203 coverage per ₹1 premium. Reliable coverage you can trust."
    },
    {
        "rank": 4,
        "plan_id": "PL10097",
        "plan_name": "Individual Health Insurance Gold",
        "provider": "Liberty General Insurance",
        "premium": 4100,
        "monthly_premium": 342,
        "deductible": 0,
        "network_size": 43,
        "coverage_amount": 405900,
        "explanation": "Highly affordable at 4.1% of annual income. Adequate ₹9L coverage. Excellent value: ₹99 coverage per ₹1 premium."
    },
    {
        "rank": 5,
        "plan_id": "PL10098",
        "plan_name": "Individual Health Insurance Bronze",
        "provider": "National Insurance Company",
        "premium": 1100,
        "monthly_premium": 92,
        "deductible": 20000,
        "network_size": 40,
        "coverage_amount": 216700,
        "explanation": "Highly affordable at 1.1% of annual income. Excellent value: ₹197 coverage per ₹1 premium. Reliable coverage you can trust."
    }
]


def create_user_profile_table():
    """Create extended user profile table in main database"""
    with app.app_context():
        # Create table for extended user profiles using text()
        from sqlalchemy import text
        with db.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL UNIQUE,
                    age INTEGER,
                    gender VARCHAR(20),
                    annual_income NUMERIC,
                    marital_status VARCHAR(50),
                    city VARCHAR(100),
                    state VARCHAR(100),
                    region VARCHAR(100),
                    occupation_type VARCHAR(100),
                    plan_type VARCHAR(50),
                    coverage_amount NUMERIC,
                    payment_mode VARCHAR(50),
                    existing_policy BOOLEAN,
                    premium_budget NUMERIC,
                    smoking_flag BOOLEAN,
                    has_diabetes BOOLEAN,
                    has_hypertension BOOLEAN,
                    has_obesity BOOLEAN,
                    has_heart_disease BOOLEAN,
                    has_cancer_history BOOLEAN,
                    claim_history_count INTEGER,
                    renewal_loyalty_years INTEGER,
                    urban_rural VARCHAR(50),
                    dependents INTEGER,
                    profile_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """))
            conn.commit()
        print("✅ Created user_profiles table")


def setup_user1():
    """Create or update User 1 with profile data"""
    with app.app_context():
        from sqlalchemy import text
        
        # Check if user exists
        user = User.query.filter_by(email=USER1_PROFILE["email"]).first()
        
        if not user:
            # Try to find by username
            user = User.query.filter_by(username=USER1_PROFILE["username"]).first()
        
        if user:
            print(f"✅ User 1 already exists: {user.email} (ID: {user.id})")
            # Update password
            user.set_password(USER1_PROFILE["password"])
            db.session.commit()
            print(f"✅ Updated User 1 password")
        else:
            # Create new user
            user = User(
                username=USER1_PROFILE["username"],
                email=USER1_PROFILE["email"]
            )
            user.set_password(USER1_PROFILE["password"])
            db.session.add(user)
            db.session.commit()
            print(f"✅ Created User 1: {user.email} (ID: {user.id})")
        
        # Insert or update extended profile
        profile_json = json.dumps({k: v for k, v in USER1_PROFILE.items() 
                                  if k not in ['email', 'username', 'password']})
        
        # Check if profile exists
        with db.engine.connect() as conn:
            result = conn.execute(
                text("SELECT id FROM user_profiles WHERE user_id = :user_id"),
                {"user_id": user.id}
            ).fetchone()
            
            if result:
                # Update existing profile
                conn.execute(text("""
                    UPDATE user_profiles SET
                        age = :age, gender = :gender, annual_income = :annual_income,
                        marital_status = :marital_status, city = :city, state = :state,
                        region = :region, occupation_type = :occupation_type,
                        plan_type = :plan_type, coverage_amount = :coverage_amount,
                        payment_mode = :payment_mode, existing_policy = :existing_policy,
                        premium_budget = :premium_budget, smoking_flag = :smoking_flag,
                        has_diabetes = :has_diabetes, has_hypertension = :has_hypertension,
                        has_obesity = :has_obesity, has_heart_disease = :has_heart_disease,
                        has_cancer_history = :has_cancer_history,
                        claim_history_count = :claim_history_count,
                        renewal_loyalty_years = :renewal_loyalty_years,
                        urban_rural = :urban_rural, dependents = :dependents,
                        profile_json = :profile_json,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id
                """), {
                    "user_id": user.id,
                    "age": USER1_PROFILE["age"],
                    "gender": USER1_PROFILE["gender"],
                    "annual_income": USER1_PROFILE["annual_income"],
                    "marital_status": USER1_PROFILE["marital_status"],
                    "city": USER1_PROFILE["city"],
                    "state": USER1_PROFILE["state"],
                    "region": USER1_PROFILE["region"],
                    "occupation_type": USER1_PROFILE["occupation_type"],
                    "plan_type": USER1_PROFILE["plan_type"],
                    "coverage_amount": USER1_PROFILE["coverage_amount"],
                    "payment_mode": USER1_PROFILE["payment_mode"],
                    "existing_policy": USER1_PROFILE["existing_policy"],
                    "premium_budget": USER1_PROFILE["premium_budget"],
                    "smoking_flag": USER1_PROFILE["smoking_flag"],
                    "has_diabetes": USER1_PROFILE["has_diabetes"],
                    "has_hypertension": USER1_PROFILE["has_hypertension"],
                    "has_obesity": USER1_PROFILE["has_obesity"],
                    "has_heart_disease": USER1_PROFILE["has_heart_disease"],
                    "has_cancer_history": USER1_PROFILE["has_cancer_history"],
                    "claim_history_count": USER1_PROFILE["claim_history_count"],
                    "renewal_loyalty_years": USER1_PROFILE["renewal_loyalty_years"],
                    "urban_rural": USER1_PROFILE["urban_rural"],
                    "dependents": USER1_PROFILE["dependents"],
                    "profile_json": profile_json
                })
                print("✅ Updated User 1 profile")
            else:
                # Insert new profile
                conn.execute(text("""
                    INSERT INTO user_profiles (
                        user_id, age, gender, annual_income, marital_status,
                        city, state, region, occupation_type, plan_type,
                        coverage_amount, payment_mode, existing_policy,
                        premium_budget, smoking_flag, has_diabetes, has_hypertension,
                        has_obesity, has_heart_disease, has_cancer_history,
                        claim_history_count, renewal_loyalty_years, urban_rural,
                        dependents, profile_json
                    ) VALUES (
                        :user_id, :age, :gender, :annual_income, :marital_status,
                        :city, :state, :region, :occupation_type, :plan_type,
                        :coverage_amount, :payment_mode, :existing_policy,
                        :premium_budget, :smoking_flag, :has_diabetes, :has_hypertension,
                        :has_obesity, :has_heart_disease, :has_cancer_history,
                        :claim_history_count, :renewal_loyalty_years, :urban_rural,
                        :dependents, :profile_json
                    )
                """), {
                    "user_id": user.id,
                    "age": USER1_PROFILE["age"],
                    "gender": USER1_PROFILE["gender"],
                    "annual_income": USER1_PROFILE["annual_income"],
                    "marital_status": USER1_PROFILE["marital_status"],
                    "city": USER1_PROFILE["city"],
                    "state": USER1_PROFILE["state"],
                    "region": USER1_PROFILE["region"],
                    "occupation_type": USER1_PROFILE["occupation_type"],
                    "plan_type": USER1_PROFILE["plan_type"],
                    "coverage_amount": USER1_PROFILE["coverage_amount"],
                    "payment_mode": USER1_PROFILE["payment_mode"],
                    "existing_policy": USER1_PROFILE["existing_policy"],
                    "premium_budget": USER1_PROFILE["premium_budget"],
                    "smoking_flag": USER1_PROFILE["smoking_flag"],
                    "has_diabetes": USER1_PROFILE["has_diabetes"],
                    "has_hypertension": USER1_PROFILE["has_hypertension"],
                    "has_obesity": USER1_PROFILE["has_obesity"],
                    "has_heart_disease": USER1_PROFILE["has_heart_disease"],
                    "has_cancer_history": USER1_PROFILE["has_cancer_history"],
                    "claim_history_count": USER1_PROFILE["claim_history_count"],
                    "renewal_loyalty_years": USER1_PROFILE["renewal_loyalty_years"],
                    "urban_rural": USER1_PROFILE["urban_rural"],
                    "dependents": USER1_PROFILE["dependents"],
                    "profile_json": profile_json
                })
                print("✅ Created User 1 profile")
            
            conn.commit()
        
        return user


def link_recommendations_to_user(user):
    """Link existing lead recommendations to User 1 or create new ones"""
    # Connect to leads database
    leads_db_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'data', 'leads.db'
    )
    
    if not os.path.exists(leads_db_path):
        print(f"⚠️  Leads database not found at {leads_db_path}")
        print("   Creating new lead with recommendations...")
        create_lead_with_recommendations(user)
        return
    
    conn = sqlite3.connect(leads_db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Find most recent lead for anonymous user or create new one
    lead = cur.execute("""
        SELECT * FROM leads 
        WHERE user_id = ? OR user_id = 'anonymous'
        ORDER BY timestamp DESC LIMIT 1
    """, (str(user.id),)).fetchone()
    
    if lead:
        lead_id = lead['id']
        print(f"✅ Found existing lead ID: {lead_id}")
        
        # Update lead to associate with User 1
        cur.execute("UPDATE leads SET user_id = ? WHERE id = ?", 
                   (str(user.id), lead_id))
        conn.commit()
        print(f"✅ Linked lead {lead_id} to User 1")
        
        # Show recommendations
        recs = cur.execute("""
            SELECT * FROM recommendations 
            WHERE lead_id = ? 
            ORDER BY rank
        """, (lead_id,)).fetchall()
        
        print(f"\n📊 Recommendations for User 1:")
        for rec in recs:
            print(f"   #{rec['rank']} {rec['plan_name']} - {rec['provider']}")
    else:
        print("ℹ️  No existing leads found. Creating new lead...")
        create_lead_with_recommendations(user)
    
    conn.close()


def create_lead_with_recommendations(user):
    """Create a new lead with the expected recommendations"""
    from app.services.persistence import save_lead_and_recs
    
    # Prepare profile dict
    profile_dict = {k: v for k, v in USER1_PROFILE.items() 
                   if k not in ['email', 'username', 'password']}
    
    # Prepare recommendations list
    recs_list = [
        {
            'plan_id': r['plan_id'],
            'plan_name': r['plan_name'],
            'provider': r['provider'],
            'score': 1.0 - (r['rank'] - 1) * 0.1  # Generate decreasing scores
        }
        for r in EXPECTED_RECOMMENDATIONS
    ]
    
    # Save lead and recommendations
    lead_id = save_lead_and_recs(
        user_id=str(user.id),
        profile_dict=profile_dict,
        recommendations_list=recs_list,
        source='setup_script'
    )
    
    print(f"✅ Created new lead ID {lead_id} with {len(recs_list)} recommendations")


def main():
    """Main setup function"""
    print("=" * 60)
    print("Setting up User 1 Profile with Recommendations")
    print("=" * 60)
    
    # Create profile table
    create_user_profile_table()
    
    # Setup User 1
    user = setup_user1()
    
    # Link recommendations
    link_recommendations_to_user(user)
    
    print("\n" + "=" * 60)
    print("✅ Setup Complete!")
    print("=" * 60)
    print(f"\nUser 1 Login Credentials:")
    print(f"  Email: {USER1_PROFILE['email']}")
    print(f"  Password: {USER1_PROFILE['password']}")
    print(f"\nProfile Summary:")
    print(f"  Age: {USER1_PROFILE['age']}, Gender: {USER1_PROFILE['gender']}")
    print(f"  Income: ₹{USER1_PROFILE['annual_income']:,}")
    print(f"  City: {USER1_PROFILE['city']}, {USER1_PROFILE['state']}")
    print(f"  Health Conditions: Diabetes, Hypertension, Obesity")
    print(f"  Premium Budget: ₹{USER1_PROFILE['premium_budget']:,}/month")
    print(f"\nYou can now:")
    print(f"  1. Login at http://127.0.0.1:5001/login")
    print(f"  2. View dashboard at http://127.0.0.1:5001/dashboard")
    print()


if __name__ == "__main__":
    main()
