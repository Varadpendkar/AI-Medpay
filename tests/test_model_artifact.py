"""Test that model artifact exists and PlanRanker loads."""
from backend.app.main import ranker


def test_ranker_loaded():
    assert ranker is not None, "PlanRanker should be initialized (RANKER_MODEL_PATH must point to model)"
