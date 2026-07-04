from app import compute_readiness_score


def test_scoring_returns_status_and_bounds() -> None:
    evidences = [{"impact_level": 5}] * 5
    gaps = [{"severity": "critical", "status": "open"}]
    result = compute_readiness_score(evidences=evidences, gaps=gaps, completed_tasks=3)

    assert 0 <= result["score"] <= 100
    assert result["status"] in {"structured", "in_progress", "early_stage"}
    assert "Educational" in result["explanation"]


def test_scoring_penalizes_open_critical_gap() -> None:
    evidences = [{"impact_level": 4}] * 8
    no_gap = compute_readiness_score(evidences=evidences, gaps=[], completed_tasks=0)
    with_gap = compute_readiness_score(
        evidences=evidences,
        gaps=[{"severity": "critical", "status": "open"}],
        completed_tasks=0,
    )
    assert with_gap["score"] < no_gap["score"]
