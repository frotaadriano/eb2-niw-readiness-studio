from app import load_locale, t


def test_locale_key_parity_minimum() -> None:
    pt = load_locale("pt-BR")
    en = load_locale("en-US")
    assert set(pt.keys()) == set(en.keys())


def test_fallback_to_english_locale() -> None:
    unknown = load_locale("fr-FR")
    en = load_locale("en-US")
    assert unknown == en


def test_missing_key_returns_key_name() -> None:
    assert t("en-US", "missing.key") == "missing.key"
