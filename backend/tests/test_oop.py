# backend/tests/test_oop.py
import pytest
from app.utils.oop import load_procedures, estimate_oop_for_plan


def test_load_procs():
    """Test that procedures CSV loads successfully"""
    df = load_procedures()
    assert not df.empty
    assert 'procedure_code' in df.columns
    assert 'avg_cost' in df.columns


def test_mri_oop():
    """Test OOP estimation for MRI procedure"""
    df = load_procedures()
    plan = {
        "coverage_amount": 100000,
        "deductible": 5000,
        "copay_pct": 10,
        "network_size": 80
    }
    user = {"age": 35, "income": 600000}

    # MRI_BRAIN should exist in procedures CSV
    oop, breakdown = estimate_oop_for_plan(
        "MRI_BRAIN", user, plan, procedures_df=df)

    assert isinstance(oop, (float, int))
    assert oop >= 0
    assert breakdown["oop"] == oop
    assert "total_cost" in breakdown
    assert "deductible_applied" in breakdown
    assert "copay_amount" in breakdown
    assert "reimbursable" in breakdown


def test_knee_replacement_oop():
    """Test OOP for high-cost procedure (Knee Replacement)"""
    df = load_procedures()
    plan = {
        "coverage_amount": 500000,
        "deductible": 10000,
        "copay_pct": 20,
        "network_size": 150
    }
    user = {"age": 60, "income": 1200000}

    oop, breakdown = estimate_oop_for_plan(
        "KNEE_REPLACEMENT", user, plan, procedures_df=df)

    assert isinstance(oop, (float, int))
    assert oop >= 0
    # Knee replacement is expensive, OOP should be substantial
    assert breakdown["total_cost"] > 100000
    # Should have network discount
    assert breakdown["network_discount_pct"] > 0


def test_zero_coverage_plan():
    """Test OOP when plan has zero coverage"""
    df = load_procedures()
    plan = {
        "coverage_amount": 0,
        "deductible": 0,
        "copay_pct": 0,
        "network_size": 0
    }
    user = {"age": 30, "income": 400000}

    oop, breakdown = estimate_oop_for_plan(
        "ANGIOPLASTY", user, plan, procedures_df=df)

    # With no coverage, OOP should equal total cost
    assert oop == breakdown["total_cost"]
    assert breakdown["reimbursable"] == 0


def test_unknown_proc():
    """Test that unknown procedure raises ValueError"""
    with pytest.raises(ValueError, match="Unknown procedure_code"):
        estimate_oop_for_plan("UNKNOWN_PROC_12345", {}, {"coverage_amount": 0})


def test_network_discount():
    """Test that network size affects discount"""
    df = load_procedures()
    user = {"age": 40, "income": 800000}

    # Small network (should get minimal or no discount)
    plan_small = {
        "coverage_amount": 200000,
        "deductible": 5000,
        "copay_pct": 10,
        "network_size": 30
    }

    # Large network (should get discount)
    plan_large = {
        "coverage_amount": 200000,
        "deductible": 5000,
        "copay_pct": 10,
        "network_size": 250
    }

    oop_small, breakdown_small = estimate_oop_for_plan(
        "HERNIA_REPAIR", user, plan_small, procedures_df=df)
    oop_large, breakdown_large = estimate_oop_for_plan(
        "HERNIA_REPAIR", user, plan_large, procedures_df=df)

    # Larger network should result in lower OOP
    assert breakdown_large["network_discount_pct"] > breakdown_small["network_discount_pct"]


def test_high_deductible_impact():
    """Test that high deductible increases OOP"""
    df = load_procedures()
    user = {"age": 45, "income": 900000}

    plan_low_deduct = {
        "coverage_amount": 300000,
        "deductible": 1000,
        "copay_pct": 10,
        "network_size": 100
    }

    plan_high_deduct = {
        "coverage_amount": 300000,
        "deductible": 50000,
        "copay_pct": 10,
        "network_size": 100
    }

    oop_low, _ = estimate_oop_for_plan(
        "APPENDECTOMY", user, plan_low_deduct, procedures_df=df)
    oop_high, _ = estimate_oop_for_plan(
        "APPENDECTOMY", user, plan_high_deduct, procedures_df=df)

    # Higher deductible should result in higher OOP
    assert oop_high > oop_low
