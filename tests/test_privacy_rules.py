from app import filter_private_evidences


def test_filter_private_evidences_removes_private_items() -> None:
    evidences = [
        {"id": 1, "is_private": False},
        {"id": 2, "is_private": True},
        {"id": 3, "is_private": False},
    ]
    filtered = filter_private_evidences(evidences)
    assert [item["id"] for item in filtered] == [1, 3]
