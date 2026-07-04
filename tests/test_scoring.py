from app import calculate_eb2_scores, classify_readiness


def test_overall_score_with_weights() -> None:
    questions = [
        {"category_key": "assessment.category.academic", "weight": 5, "score": 5},
        {"category_key": "assessment.category.experience", "weight": 1, "score": 0},
    ]
    result = calculate_eb2_scores(questions)
    # (5*5 + 0*1) / (6*5) * 100 = 83.33 -> 83
    assert result["overall_score"] == 83


def test_score_by_category() -> None:
    questions = [
        {"category_key": "assessment.category.academic", "weight": 2, "score": 5},
        {"category_key": "assessment.category.academic", "weight": 1, "score": 0},
        {"category_key": "assessment.category.experience", "weight": 1, "score": 5},
    ]
    result = calculate_eb2_scores(questions)

    assert result["dimension_scores"]["assessment.category.academic"] == 67
    assert result["dimension_scores"]["assessment.category.experience"] == 100


def test_classification_boundaries() -> None:
    assert classify_readiness(0) == "low"
    assert classify_readiness(39) == "low"
    assert classify_readiness(40) == "initial"
    assert classify_readiness(59) == "initial"
    assert classify_readiness(60) == "moderate"
    assert classify_readiness(74) == "moderate"
    assert classify_readiness(75) == "strong"
    assert classify_readiness(89) == "strong"
    assert classify_readiness(90) == "robust"


def test_no_answers_returns_zero() -> None:
    questions = [
        {"category_key": "assessment.category.academic", "weight": 3, "score": None},
        {"category_key": "assessment.category.experience", "weight": 2, "score": None},
    ]
    result = calculate_eb2_scores(questions)

    assert result["overall_score"] == 0
    assert result["classification"] == "low"


def test_weights_change_overall_score() -> None:
    heavy = [
        {"category_key": "assessment.category.academic", "weight": 5, "score": 5},
        {"category_key": "assessment.category.experience", "weight": 1, "score": 1},
    ]
    balanced = [
        {"category_key": "assessment.category.academic", "weight": 1, "score": 5},
        {"category_key": "assessment.category.experience", "weight": 1, "score": 1},
    ]

    heavy_result = calculate_eb2_scores(heavy)
    balanced_result = calculate_eb2_scores(balanced)

    assert heavy_result["overall_score"] > balanced_result["overall_score"]
