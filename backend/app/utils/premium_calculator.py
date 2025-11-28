"""
Premium Calculator for Health Insurance Plans
Calculates realistic premiums based on user profile and risk factors
"""
import logging

logger = logging.getLogger(__name__)


class PremiumCalculator:
    """Calculate realistic health insurance premiums"""
    
    # Base premium per lakh of coverage (annual)
    BASE_PREMIUM_PER_LAKH = {
        '18-25': 500,   # ₹500 per lakh for young adults
        '26-35': 750,   # ₹750 per lakh
        '36-45': 1200,  # ₹1200 per lakh
        '46-55': 2000,  # ₹2000 per lakh
        '56-65': 3500,  # ₹3500 per lakh
        '65+': 5000     # ₹5000 per lakh for seniors
    }
    
    # Loading factors for pre-existing conditions (percentage increase)
    CONDITION_LOADING = {
        'diabetes': 25,      # 25% increase
        'hypertension': 20,  # 20% increase
        'heart_disease': 40, # 40% increase
        'obesity': 15,       # 15% increase
        'asthma': 10,        # 10% increase
        'thyroid': 8,        # 8% increase
    }
    
    # Deductible discount (percentage decrease in premium)
    DEDUCTIBLE_DISCOUNT = {
        0: 0,           # No deductible = no discount
        25000: 10,      # ₹25k deductible = 10% off
        50000: 15,      # ₹50k deductible = 15% off
        100000: 20,     # ₹1L deductible = 20% off
        200000: 25,     # ₹2L deductible = 25% off
    }
    
    @staticmethod
    def get_age_band(age: int) -> str:
        """Get age band for premium calculation"""
        if age <= 25:
            return '18-25'
        elif age <= 35:
            return '26-35'
        elif age <= 45:
            return '36-45'
        elif age <= 55:
            return '46-55'
        elif age <= 65:
            return '56-65'
        else:
            return '65+'
    
    @staticmethod
    def calculate_base_premium(coverage_amount: float, age: int) -> float:
        """
        Calculate base premium based on coverage and age
        
        Args:
            coverage_amount: Sum insured amount in rupees
            age: User's age
            
        Returns:
            Annual base premium in rupees
        """
        age_band = PremiumCalculator.get_age_band(age)
        premium_per_lakh = PremiumCalculator.BASE_PREMIUM_PER_LAKH[age_band]
        coverage_in_lakhs = coverage_amount / 100000
        
        # Base premium calculation
        base_premium = coverage_in_lakhs * premium_per_lakh
        
        return base_premium
    
    @staticmethod
    def apply_condition_loading(base_premium: float, conditions: list) -> tuple:
        """
        Apply loading for pre-existing conditions
        
        Args:
            base_premium: Base premium amount
            conditions: List of condition names (e.g., ['diabetes', 'hypertension'])
            
        Returns:
            Tuple of (adjusted_premium, total_loading_percentage)
        """
        total_loading = 0
        
        for condition in conditions:
            condition_lower = condition.lower()
            if condition_lower in PremiumCalculator.CONDITION_LOADING:
                total_loading += PremiumCalculator.CONDITION_LOADING[condition_lower]
        
        # Cap total loading at 100% (double premium)
        total_loading = min(total_loading, 100)
        
        adjusted_premium = base_premium * (1 + total_loading / 100)
        
        return adjusted_premium, total_loading
    
    @staticmethod
    def apply_deductible_discount(premium: float, deductible: float) -> tuple:
        """
        Apply discount for selecting a deductible
        
        Args:
            premium: Current premium amount
            deductible: Deductible amount
            
        Returns:
            Tuple of (discounted_premium, discount_percentage)
        """
        # Find closest deductible tier
        discount_pct = 0
        for tier, discount in sorted(PremiumCalculator.DEDUCTIBLE_DISCOUNT.items()):
            if deductible >= tier:
                discount_pct = discount
        
        discounted_premium = premium * (1 - discount_pct / 100)
        
        return discounted_premium, discount_pct
    
    @staticmethod
    def calculate_realistic_premium(
        coverage_amount: float,
        age: int,
        conditions: list = None,
        deductible: float = 0,
        smoking: bool = False,
        plan_tier: str = 'standard'
    ) -> dict:
        """
        Calculate comprehensive realistic premium with breakdown
        
        Args:
            coverage_amount: Sum insured
            age: User age
            conditions: List of pre-existing conditions
            deductible: Deductible amount
            smoking: Smoking status
            plan_tier: Plan tier (basic, standard, premium)
            
        Returns:
            Dictionary with premium breakdown
        """
        conditions = conditions or []
        
        # Step 1: Base premium
        base_premium = PremiumCalculator.calculate_base_premium(coverage_amount, age)
        
        # Step 2: Tier adjustment
        tier_multiplier = {'basic': 0.8, 'standard': 1.0, 'premium': 1.3, 'super_premium': 1.6}
        tier_adjusted = base_premium * tier_multiplier.get(plan_tier, 1.0)
        
        # Step 3: Condition loading
        condition_adjusted, condition_loading = PremiumCalculator.apply_condition_loading(
            tier_adjusted, conditions
        )
        
        # Step 4: Smoking loading (additional 15% for smokers)
        smoking_loading = 0
        if smoking:
            smoking_loading = 15
            smoking_adjusted = condition_adjusted * 1.15
        else:
            smoking_adjusted = condition_adjusted
        
        # Step 5: Deductible discount
        final_premium, deductible_discount = PremiumCalculator.apply_deductible_discount(
            smoking_adjusted, deductible
        )
        
        # Round to nearest 100
        final_premium = round(final_premium / 100) * 100
        
        return {
            'annual_premium': final_premium,
            'monthly_premium': round(final_premium / 12 / 100) * 100,
            'quarterly_premium': round(final_premium / 4 / 100) * 100,
            'breakdown': {
                'base_premium': round(base_premium),
                'tier_multiplier': tier_multiplier.get(plan_tier, 1.0),
                'condition_loading_pct': condition_loading,
                'smoking_loading_pct': smoking_loading,
                'deductible_discount_pct': deductible_discount,
                'conditions_applied': conditions,
            }
        }
    
    @staticmethod
    def validate_premium_realistic(
        premium: float,
        coverage: float,
        age: int,
        conditions: list = None
    ) -> bool:
        """
        Check if a premium is realistic for given parameters
        
        Returns True if premium is within reasonable range
        """
        conditions = conditions or []
        
        # Calculate minimum expected premium (basic tier, no conditions, max deductible)
        min_calc = PremiumCalculator.calculate_realistic_premium(
            coverage, age, [], 200000, False, 'basic'
        )
        min_premium = min_calc['annual_premium']
        
        # Calculate maximum expected premium (premium tier, with conditions, no deductible)
        max_calc = PremiumCalculator.calculate_realistic_premium(
            coverage, age, conditions, 0, True, 'premium'
        )
        max_premium = max_calc['annual_premium']
        
        # Premium should be between min and max * 1.5 (allowing some variance)
        return min_premium * 0.5 <= premium <= max_premium * 1.5
