# forms.py
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, BooleanField, SubmitField,
    IntegerField, SelectField, FileField, SelectMultipleField
)
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, NumberRange, Optional
)

# Helpers for consistent input cleanup
def _strip(x):
    return x.strip() if isinstance(x, str) else x

def _lower(x):
    return x.strip().lower() if isinstance(x, str) else x


class RegisterForm(FlaskForm):
    username = StringField(
        "Username",
        filters=[_strip],
        validators=[
            DataRequired(),
            Length(min=2, max=50, message="Username must be between 2 and 50 characters."),
        ],
    )
    email = StringField(
        "Email",
        filters=[_lower],
        validators=[
            DataRequired(),
            Email(message="Please enter a valid email address."),
        ],
    )
    password = PasswordField(
        "Password",
        filters=[_strip],
        validators=[
            DataRequired(),
            Length(min=6, message="Password must be at least 6 characters."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        filters=[_strip],
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Sign up")


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        filters=[_lower],
        validators=[
            DataRequired(),
            Email(message="Please enter a valid email address."),
        ],
    )
    password = PasswordField(
        "Password",
        filters=[_strip],
        validators=[DataRequired()],
    )
    remember = BooleanField("Remember Me")
    submit = SubmitField("Log in")


class CompareForm(FlaskForm):
    # --- Existing Core Fields ---
    age = IntegerField("Age", validators=[DataRequired(), NumberRange(min=18, max=85)])
    income = IntegerField(
        "Annual Income (₹)",
        validators=[DataRequired(), NumberRange(min=0, message="Income must be ₹0 or higher.")],
    )
    dependents = IntegerField(
        "Number of Dependents",
        validators=[DataRequired(), NumberRange(min=0, max=10)],
    )
    health_status = SelectField(
        "Health Status",
        choices=[("excellent", "Excellent"), ("good", "Good"), ("fair", "Fair"), ("poor", "Poor")],
        validators=[DataRequired()],
    )
    coverage_preference = SelectField(
        "Primary Goal",
        choices=[
            ("low_premium", "Lower Premium"),
            ("balanced", "Balanced"),
            ("high_coverage", "Higher Coverage"),
        ],
        validators=[DataRequired()],
        default="balanced",
    )
    
    # ✅ --- NEW FIELDS ADDED BELOW ---

    # --- Location ---
    state = SelectField(
        "State", validators=[DataRequired()],
        choices=[
            ("Maharashtra","Maharashtra"), ("Karnataka","Karnataka"), ("Tamil Nadu","Tamil Nadu"),
            ("Telangana","Telangana"), ("Kerala","Kerala"), ("Gujarat","Gujarat"), ("Delhi","Delhi"),
            ("West Bengal","West Bengal"), ("Rajasthan","Rajasthan"), ("Uttar Pradesh","Uttar Pradesh"),
            ("Madhya Pradesh","Madhya Pradesh"), ("Punjab","Punjab"), ("Haryana","Haryana"),
        ],
        default="Maharashtra",
    )
    city = StringField("City (optional)", validators=[Optional()])
    pincode = IntegerField("Pincode (optional)", validators=[Optional(), NumberRange(min=100000, max=999999)])
    
    # --- Preferred providers / hospitals ---
    preferred_providers = SelectMultipleField(
        "Preferred Providers (optional)", validators=[Optional()],
        choices=[
            ("StarHealth","Star Health"), ("HDFC ERGO","HDFC ERGO"), ("Niva Bupa","Niva Bupa"),
            ("ICICI Lombard","ICICI Lombard"), ("Care Health","Care Health"),
            ("Aditya Birla","Aditya Birla"), ("ManipalCigna","ManipalCigna"),
            ("Reliance Health","Reliance Health"), ("TATA AIG","TATA AIG"), ("Bajaj Allianz","Bajaj Allianz"),
        ]
    )
    preferred_hospital = StringField("Preferred Hospital (optional)", validators=[Optional()])
    in_network_only = BooleanField("Only show in-network plans", default=False)
    
    # --- Coverage target ---
    target_coverage = IntegerField(
        "Target Coverage (₹)", validators=[Optional(), NumberRange(min=100000, max=10000000)]
    )
    
    # --- Affordability guardrail ---
    max_premium = IntegerField(
        "Max Annual Premium (₹)", validators=[Optional(), NumberRange(min=500, max=1000000)]
    )

    current_policy_file = FileField(
        "Upload Current Policy (PDF/Image) — optional",
        validators=[Optional()],
    )
    submit = SubmitField("Get AI Recommendation")