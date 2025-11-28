#!/usr/bin/env python3
"""
New Plan Ranker using the trained LightGBM model (plan_ranker.pkl)
This integrates the Model folder's recommendation system into the backend.
"""
import os
import pickle
import logging
from pathlib import Path
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ========== DEBUG INSTRUMENTATION ==========
debug_logger = logging.getLogger("planranker_debug")
debug_logger.setLevel(logging.INFO)


def log_feature_matrix_info(X, tag="FEATURES"):
    """
    X: pandas.DataFrame (n_candidates x n_features)
    """
    try:
        debug_logger.info("---- %s: shape=%s", tag, X.shape)
        debug_logger.info("---- %s: columns=%s", tag,
                          list(X.columns)[:20])  # first 20 cols
        # head as dict to avoid huge prints
        debug_logger.info("---- %s: head(sample rows)=%s",
                          tag, X.head(3).to_dict(orient='list'))

        # Describe numeric columns
        numeric_cols = X.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            desc = X[numeric_cols].describe().to_dict()
            # log means + min/max for numeric columns
            sample_desc = {k: {"mean": float(v.get("mean", 0)), "min": float(v.get("min", 0)), "max": float(v.get("max", 0))}
                           for k, v in list(desc.items())[:10] if "mean" in v}
            debug_logger.info("---- %s: desc(sample)=%s", tag, sample_desc)

        # unique rows check
        unique_rows = X.drop_duplicates().shape[0]
        debug_logger.info("---- %s: unique_rows=%d (out of %d)",
                          tag, unique_rows, X.shape[0])

        # column variance
        variances = X[numeric_cols].var(
            axis=0).to_dict() if len(numeric_cols) > 0 else {}
        const_feats = [k for k, v in variances.items() if float(v) == 0.0]
        low_var = [k for k, v in variances.items() if 0.0 < float(v) < 1e-8]
        debug_logger.info("---- %s: constant_features(%d)=%s",
                          tag, len(const_feats), const_feats[:20])
        if low_var:
            debug_logger.info(
                "---- %s: low_variance_features(sample)=%s", tag, low_var[:20])
    except Exception as e:
        debug_logger.exception("log_feature_matrix_info failed: %s", e)

# ========== END DEBUG INSTRUMENTATION ==========


class NewPlanRanker:
    """
    Insurance Plan Recommender using trained LightGBM ranking model
    """

    def __init__(self, project_root: Path):
        self.root = Path(project_root)

        # Load model from backend/models directory
        model_path = self.root.parent / "models" / "plan_ranker.pkl"

        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found at {model_path}. "
                "Please ensure plan_ranker.pkl exists in backend/models/"
            )

        print(f"Loading model from: {model_path}")

        # Load model artifacts
        with open(model_path, 'rb') as f:
            artifacts = pickle.load(f)
            self.model = artifacts['model']
            # Try both 'feature_cols' (from new training) and 'feature_columns' (legacy)
            self.feature_columns = artifacts.get(
                'feature_cols', artifacts.get('feature_columns', []))
            self.label_encoders = artifacts.get('label_encoders', {})
            self.feature_importance = artifacts.get('feature_importance', {})

        # If still empty, try to recover from model booster
        if not self.feature_columns:
            try:
                self.feature_columns = list(self.model.booster_.feature_name())
                logger.warning("Recovered %d feature names from model.booster_.feature_name()", len(
                    self.feature_columns))
            except Exception as e:
                logger.error(
                    "Could not recover feature names from model: %s", e)
                self.feature_columns = []

        print(f"✓ Model loaded with {len(self.feature_columns)} features")

        # Load data from backend/models directory (contains the new data files)
        data_dir = self.root.parent / "models"

        # Load plans
        self.plans = pd.read_csv(data_dir / "plans.csv")

        # Load network data
        plan_hospital_map = pd.read_csv(
            data_dir / "plan_hospital_map_large.csv")
        hospitals = pd.read_csv(data_dir / "hospitals_large.csv")

        # Prepare plan network features
        network_stats = plan_hospital_map.groupby('plan_id').agg({
            'hospital_id': 'count',
            'distance_score': 'mean',
            'contract_type': [
                lambda x: (x == 'cashless').sum() / len(x) * 100,
                lambda x: (x == 'reimbursement').sum() / len(x) * 100
            ]
        }).reset_index()
        network_stats.columns = ['planid', 'network_size_actual', 'avg_distance_score',
                                 'cashless_percentage', 'reimbursement_percentage']

        self.plans = self.plans.merge(network_stats, on='planid', how='left')
        self.plans['networksize'] = self.plans['network_size_actual'].fillna(
            self.plans['networksize'])
        self.plans = self.plans.drop('network_size_actual', axis=1)

        # Add hospital states
        hospital_states = hospitals[['hospital_id', 'state']].copy()
        plan_hospital_with_state = plan_hospital_map.merge(
            hospital_states, on='hospital_id', how='left')
        plan_states = plan_hospital_with_state.groupby('plan_id')['state'].apply(
            lambda x: ','.join(sorted(set(x.dropna())))
        ).reset_index()
        plan_states.columns = ['planid', 'hospital_states']
        self.plans = self.plans.merge(plan_states, on='planid', how='left')

        print(f"✓ Loaded {len(self.plans)} plans with network features")

    def _create_derived_features(self, user: dict, plans_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create features matching the trained model (18 features from train_plan_ranker_v2.py)
        This replaces the old 48-feature system with the new personalized feature set.
        """
        df = plans_df.copy()

        # Extract user attributes (with defaults)
        user_age = user.get('age', 35)
        user_income_band = user.get('income_band', '6-10L')
        user_smoking = user.get(
            'smoking_status', user.get('smoking_flag', 'no'))
        user_dependents = user.get(
            'dependents', user.get('dependents_count', 0))
        user_claim_history = user.get('claim_history_count', 0)
        user_renewal = user.get('renewal_loyalty_years', 0)
        user_risk = user.get('risk_score', 0.5)

        # Map income band to numeric
        def map_income_band_to_numeric(income_band):
            mapping = {
                '<3L': 250000,
                '3-6L': 450000,
                '6-10L': 800000,
                '10-20L': 1500000,
                '>20L': 2500000
            }
            return mapping.get(str(income_band), 800000)

        user_income = map_income_band_to_numeric(user_income_band)

        # Plan attributes (map to model's expected column names)
        df['plan_premium'] = pd.to_numeric(
            df.get('premium', 0), errors='coerce').fillna(0)
        df['plan_deductible'] = pd.to_numeric(
            df.get('deductible', 0), errors='coerce').fillna(0)
        df['plan_coverage'] = pd.to_numeric(
            df.get('coverageamount', 0), errors='coerce').fillna(0)
        df['plan_network'] = pd.to_numeric(
            df.get('networksize', 0), errors='coerce').fillna(0)

        # Feature engineering (matching train_plan_ranker_v2.py)
        df['premium_income_ratio'] = df['plan_premium'] / (user_income + 1e-9)
        df['premium_coverage_ratio'] = df['plan_premium'] / \
            (df['plan_coverage'] + 1e-9)
        df['network_per_100'] = df['plan_network'] / 100.0

        # Age match: check if user age is in plan's age range
        def age_in_range(plan_age_range):
            try:
                if pd.isna(plan_age_range):
                    return 0
                age_str = str(plan_age_range).strip()
                if '-' not in age_str:
                    return 0
                parts = [int(x.strip()) for x in age_str.split("-")]
                if len(parts) == 2:
                    lo, hi = parts
                    return 1 if (lo <= user_age <= hi) else 0
            except Exception:
                pass
            return 0

        # Check if plan has age_range column
        if 'age_range' in df.columns:
            df['age_match'] = df['age_range'].apply(age_in_range)
        else:
            df['age_match'] = 0.0

        # Risk mapping
        risk_map = {"low": 0, "medium": 1, "high": 2}
        if 'risk_profile' in df.columns:
            df['risk_num'] = df['risk_profile'].fillna(
                "medium").map(risk_map).fillna(1).astype(float)
        else:
            df['risk_num'] = 1.0

        # Smoking flag
        smoking_map = {
            "yes": 1.0, "smoker": 1.0, "true": 1.0,
            "no": 0.0, "non-smoker": 0.0, "false": 0.0,
            "ex-smoker": 0.5, "ex_smoker": 0.5
        }
        smoking_val = str(user_smoking).lower()
        df['smoking_flag'] = smoking_map.get(smoking_val, 0.0)

        df['dependents_count'] = float(user_dependents)
        df['claim_history'] = float(user_claim_history)
        df['renewal_years'] = float(user_renewal)
        df['user_risk_score'] = float(user_risk)
        df['user_age'] = float(user_age)

        # Interaction features (for personalization)
        df['age_premium_interaction'] = df['user_age'] * \
            df['premium_income_ratio']
        df['income_coverage_interaction'] = (
            user_income / 1e6) * (df['plan_coverage'] / 1e6)
        df['risk_smoking_interaction'] = df['risk_num'] * df['smoking_flag']

        return df

    def _generate_explanation(self, user: dict, plan: dict, score: float) -> dict:
        """
        Generate human-readable explanation for why a plan was recommended
        WITH PERSONALIZATION for pre-existing conditions
        """
        reasons = []
        
        # Extract user conditions
        user_conditions = []
        if user.get('has_diabetes') or user.get('conditions', {}).get('diabetes'):
            user_conditions.append('Diabetes')
        if user.get('has_hypertension') or user.get('conditions', {}).get('hypertension'):
            user_conditions.append('Hypertension')
        if user.get('has_heart_disease') or user.get('conditions', {}).get('heart_disease'):
            user_conditions.append('Heart Disease')
        if user.get('has_obesity') or user.get('conditions', {}).get('obesity'):
            user_conditions.append('Obesity')

        # Premium affordability (considering user's pre-existing conditions)
        income_mapping = {
            '<3L': 2.5, '3-6L': 4.5, '6-10L': 8.0, '10-20L': 15.0, '>20L': 25.0
        }
        income_numeric = income_mapping.get(
            user.get('income_band', '6-10L'), 8.0) * 100000
        
        # Use user's actual income if provided
        if user.get('annual_income'):
            income_numeric = float(user.get('annual_income'))
        
        premium = plan.get('premium', 0)
        premium_pct = (premium * 12 / income_numeric * 100) if income_numeric > 0 else 0

        # Personalized affordability message
        if user_conditions and premium_pct < 10:
            reasons.append(
                f"Affordable even with {', '.join(user_conditions[:2])} at {premium_pct:.1f}% of annual income"
            )
        elif premium_pct < 5:
            reasons.append(
                f"Highly affordable at {premium_pct:.1f}% of annual income")
        elif premium_pct < 8:
            reasons.append(
                f"Reasonably priced at {premium_pct:.1f}% of annual income")
        elif premium_pct < 12:
            reasons.append(
                f"Within budget at {premium_pct:.1f}% of annual income")

        # Coverage amount with pre-existing condition context
        coverage = plan.get('coverageamount', 0)
        if user_conditions:
            if coverage >= 1000000:
                reasons.append(f"₹{coverage/100000:.0f}L coverage suitable for managing {', '.join(user_conditions[:2])}")
            elif coverage >= 500000:
                reasons.append(f"₹{coverage/100000:.0f}L coverage adequate for ongoing care")
        else:
            if coverage >= 1000000:
                reasons.append(f"Comprehensive ₹{coverage/100000:.0f}L coverage")
            elif coverage >= 500000:
                reasons.append(f"Adequate ₹{coverage/100000:.0f}L coverage")

        # Network size
        network = plan.get('networksize', 0)
        if network > 100:
            reasons.append(f"Extensive network of {int(network)} hospitals")
        elif network > 50:
            reasons.append(f"Good network of {int(network)} hospitals")

        # Claim approval with condition context
        rejection_rate = plan.get('claimrejectionrate', 0)
        if rejection_rate < 1.0:
            approval_rate = 100 - rejection_rate
            if user_conditions:
                reasons.append(
                    f"{approval_rate:.1f}% claim approval - reliable for chronic condition claims"
                )
            else:
                reasons.append(f"Excellent {approval_rate:.1f}% claim approval rate")
        elif rejection_rate < 2.0:
            reasons.append(f"Good {100-rejection_rate:.1f}% claim approval rate")

        # Cashless percentage
        cashless = plan.get('cashless_percentage', 0)
        if cashless > 70:
            reasons.append(f"{cashless:.0f}% cashless hospitals for hassle-free treatment")

        # Waiting period context (important for pre-existing conditions)
        waiting_period = plan.get('waitingperioddays', 730)  # Default 2 years
        if user_conditions:
            if waiting_period <= 365:
                reasons.append(f"Shorter {waiting_period} day waiting period for pre-existing conditions")
            elif waiting_period > 730:
                reasons.append(f"Note: {waiting_period} day waiting period applies to pre-existing conditions")

        # Value for money
        value_score = coverage / premium if premium > 0 else 0
        if value_score > 100:
            reasons.append(f"Excellent value: ₹{value_score:,.0f} coverage per ₹1 premium")

        # Ensure we have at least 3 reasons
        generic_reasons = [
            "AI-matched to your unique health profile",
            "Comprehensive benefits package",
            "Reliable coverage you can trust",
            "Suitable for your age group and health status"
        ]
        
        while len(reasons) < 3:
            reasons.append(generic_reasons[len(reasons)])

        return {
            'bullets': reasons[:5],  # Max 5 reasons
            'explain_text': ' | '.join(reasons[:3]),
            'explain_scores': {
                'affordability': float(100 - min(premium_pct, 100)),
                'coverage': float(min(coverage / 10000, 100)),
                'network': float(min(network / 2, 100)),
                'claim_approval': float(100 - rejection_rate)
            },
            'conditions_considered': user_conditions
        }

    def rank(self, user: dict, k: int = 8) -> list:
        """
        Rank insurance plans for a user with robust error handling

        Args:
            user: User profile dictionary
            k: Number of top plans to return

        Returns:
            List of top k ranked plans with scores and explanations.
            Returns empty list if ranking fails (logged internally).
        """
        try:
            # Filter plans by region if specified
            plans = self.plans.copy()
            
            # CRITICAL FIX: Filter out inappropriate plan types
            # Remove government schemes and life insurance products
            exclude_categories = [
                'Government Scheme',
                'PMJAY',
                'Ayushman',
                'Life Insurance',
                'Term Plan',
                'Term Insurance',
                'TROP',
                'Return of Premium'
            ]
            
            # Filter based on plan_category and plan_name
            for exclude_term in exclude_categories:
                plans = plans[
                    ~plans['plan_category'].str.contains(exclude_term, case=False, na=False) &
                    ~plans['plan_name'].str.contains(exclude_term, case=False, na=False)
                ]
            
            # Also filter out plans with ₹0 base premium (unrealistic)
            plans = plans[plans['premium'] > 0]
            
            logger.info(f"✅ Filtered to {len(plans)} valid health insurance plans (excluded govt schemes & life insurance)")

            user_id_short = str(user.get('user_id', 'unknown'))[:8]
            debug_logger.info("==== RANKING FOR USER: %s (age=%s, city=%s, budget=%s) ====",
                              user_id_short, user.get('age'), user.get('city'), user.get('premium_budget'))

            # Create features with error handling
            try:
                features_df = self._create_derived_features(user, plans)
                debug_logger.info(
                    "---- Features created: shape=%s", features_df.shape)
            except KeyError as e:
                logger.error(
                    f"❌ Missing required feature in user profile: {e}")
                return []
            except Exception as e:
                logger.exception("❌ Feature creation failed")
                return []

            # Prepare feature matrix
            # --- FIX START: Defensive Feature Handling for PlanRanker ---
            try:
                X_full = features_df
            except Exception as e:
                logger.exception(
                    "Preprocessing failed while building user features: %s", e)
                raise

            if not isinstance(X_full, pd.DataFrame):
                X_full = pd.DataFrame(X_full)

            debug_logger.info(
                "🔧 DEBUG: Preprocessed feature matrix shape: %s", X_full.shape)
            debug_logger.info(
                "🔧 DEBUG: Preprocessed feature columns: %s", list(X_full.columns)[:20])

            # Load expected training feature columns
            expected_cols = self.feature_columns

            # Try to recover from model metadata if not stored
            if not expected_cols:
                try:
                    expected_cols = list(self.model.booster_.feature_name())
                    logger.info(
                        "Recovered feature names from model.booster_.feature_name()")
                except Exception:
                    expected_cols = list(X_full.columns)
                    logger.warning(
                        "Fallback: Using current X columns as expected features.")

            # Add missing columns with zeros to match expected schema
            missing_cols = [
                c for c in expected_cols if c not in X_full.columns]
            if missing_cols:
                logger.warning(
                    "⚠️ Missing features detected: %s — filling with zeros.", missing_cols)
                for col in missing_cols:
                    X_full[col] = 0.0

            # Ensure exact column order
            X_full = X_full[expected_cols].astype(float)

            # Final sanity check
            if X_full.shape[1] == 0:
                logger.error(
                    "❌ Feature matrix empty after alignment! Aborting ranking.")
                raise ValueError(
                    "Feature matrix empty — check preprocessing or model feature list.")

            debug_logger.info("✅ Final feature matrix shape: %s", X_full.shape)
            debug_logger.info(
                "✅ Final feature columns (first 10): %s", expected_cols[:10])

            # Log feature matrix info
            log_feature_matrix_info(
                X_full, tag=f"FEATURE_MATRIX_{user_id_short}")

            # Run model prediction safely
            debug_logger.info("---- Calling model.predict() ----")
            try:
                scores = self.model.predict(X_full)

                # Guard against nearly constant predictions (add tiny jitter to avoid zero variance)
                if np.isclose(np.std(scores), 0.0, atol=1e-6):
                    logger.warning(
                        "⚠️ Predictions have near-zero variance - adding tiny jitter for normalization")
                    scores = scores + np.linspace(-1e-6, 1e-6, num=len(scores))

                logger.info(
                    "🎯 Model predictions generated successfully (shape=%s).", scores.shape)
            except Exception as e:
                logger.exception("❌ Model prediction failed: %s", e)
                raise
            # --- FIX END ---

            # Log raw predictions
            debug_logger.info("---- RAW_PRED: min=%.6f max=%.6f mean=%.6f std=%.6f",
                              scores.min(), scores.max(), scores.mean(), scores.std())
            debug_logger.info("---- RAW_PRED: unique_values=%s",
                              np.unique(scores)[:20])
            debug_logger.info(
                "---- RAW_PRED: sample(first 10)=%s", scores[:10].tolist())

            # Create results
            results = plans.copy()
            results['score'] = scores

            # Sort by score
            results = results.sort_values('score', ascending=False).head(k)

            # Format recommendations
            recommendations = []
            for idx, (_, row) in enumerate(results.iterrows(), 1):
                plan_dict = row.to_dict()
                
                # CRITICAL FIX: Calculate realistic premium with condition loading
                try:
                    from app.utils.premium_calculator import PremiumCalculator
                except ImportError:
                    # Fallback for standalone execution
                    from backend.app.utils.premium_calculator import PremiumCalculator
                
                # Extract user conditions
                conditions = []
                if user.get('has_diabetes') or user.get('conditions', {}).get('diabetes'):
                    conditions.append('diabetes')
                if user.get('has_hypertension') or user.get('conditions', {}).get('hypertension'):
                    conditions.append('hypertension')
                if user.get('has_heart_disease') or user.get('conditions', {}).get('heart_disease'):
                    conditions.append('heart_disease')
                if user.get('has_obesity') or user.get('conditions', {}).get('obesity'):
                    conditions.append('obesity')
                
                # Get plan details
                coverage = float(plan_dict.get('coverageamount', user.get('coverage_amount', 500000)))
                age = int(user.get('age', 35))
                deductible = float(plan_dict.get('deductible', 0))
                smoking = user.get('smoking_flag', 'false') in ['true', 'yes', True, 1, '1']
                plan_tier = str(plan_dict.get('plan_tier', 'standard')).lower()
                
                # Calculate realistic premium
                premium_calc = PremiumCalculator.calculate_realistic_premium(
                    coverage_amount=coverage,
                    age=age,
                    conditions=conditions,
                    deductible=deductible,
                    smoking=smoking,
                    plan_tier=plan_tier
                )
                
                # Use calculated premium (more realistic than database value)
                annual_premium = premium_calc['annual_premium']
                monthly_premium = premium_calc['monthly_premium']
                
                # Validate: If database premium is way off, log warning
                db_premium = float(plan_dict.get('premium', 0))
                if db_premium > 0:
                    if not PremiumCalculator.validate_premium_realistic(db_premium, coverage, age, conditions):
                        logger.warning(
                            f"⚠️ Plan {plan_dict.get('plan_name')} has unrealistic DB premium ₹{db_premium:,.0f}. "
                            f"Adjusted to ₹{annual_premium:,.0f} based on age {age}, conditions {conditions}"
                        )

                # Generate explanation
                explanation = self._generate_explanation(
                    user,
                    {**plan_dict, 'premium': annual_premium},  # Use realistic premium for explanation
                    plan_dict['score']
                )

                # Build recommendation
                rec = {
                    'rank': idx,
                    'plan_id': str(plan_dict.get('planid', '')),
                    'plan_name': str(plan_dict.get('plan_name', '')),
                    'provider': str(plan_dict.get('provider', '')),
                    'premium': float(annual_premium),  # FIXED: Realistic annual premium
                    'monthly_premium': float(monthly_premium),  # FIXED: Realistic monthly premium
                    'deductible': float(deductible),
                    'copay': float(plan_dict.get('copay', 0)),
                    'coverage_amount': float(coverage),
                    'network_size': int(plan_dict.get('networksize', 0)),
                    'claim_rejection_rate': float(plan_dict.get('claimrejectionrate', 0)),
                    'score': float(plan_dict['score']),
                    'bullets': explanation['bullets'],
                    'explain_text': explanation['explain_text'],
                    'explain_scores': explanation['explain_scores'],
                    'plan_type': str(plan_dict.get('plan_type', 'individual')),
                    'plan_category': str(plan_dict.get('plan_category', '')),
                    'premium_breakdown': premium_calc['breakdown'],  # NEW: Show breakdown
                    'conditions_considered': explanation.get('conditions_considered', [])  # NEW: Show conditions
                }

                recommendations.append(rec)

            return recommendations

        except KeyError as e:
            logger.error(f"❌ Missing feature in user profile: {e}")
            return []
        except Exception as e:
            logger.exception("❌ Plan ranking failed")
            return []
