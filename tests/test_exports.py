from app import build_export_payload


def test_export_omits_private_evidences() -> None:
    profile = {"full_name": "Demo"}
    evidences = [
        {"title": "Public Item", "is_private": False},
        {"title": "Private Item", "is_private": True},
    ]

    payload = build_export_payload(profile, evidences)
    titles = [ev["title"] for ev in payload["evidences"]]
    assert "Public Item" in titles
    assert "Private Item" not in titles
    assert "Educational" in payload["disclaimer"]
