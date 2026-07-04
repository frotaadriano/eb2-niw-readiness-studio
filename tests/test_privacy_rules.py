from app import filter_ai_allowed_evidences, filter_private_evidences


def test_filter_private_evidences_removes_private_items() -> None:
    evidences = [
        {"id": 1, "is_private": False},
        {"id": 2, "is_private": True},
        {"id": 3, "is_private": False},
    ]
    filtered = filter_private_evidences(evidences)
    assert [item["id"] for item in filtered] == [1, 3]


def test_filter_ai_allowed_evidences_respects_send_flag() -> None:
    evidences = [
        {"id": 1, "is_private": False, "can_send_to_ai": True},
        {"id": 2, "is_private": False, "can_send_to_ai": False},
        {"id": 3, "is_private": True, "can_send_to_ai": True},
    ]
    filtered = filter_ai_allowed_evidences(evidences)
    assert [item["id"] for item in filtered] == [1]
