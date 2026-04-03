# tests/test_pii_filter.py
from puppet_ai.core.pii_filter import PiiFilter


def test_mask_api_key():
    f = PiiFilter()
    text = "My key is sk-1234567890abcdef1234567890abcdef"
    masked = f.mask_text(text)
    assert "sk-1234567890abcdef1234567890abcdef" not in masked
    assert "sk-1***" in masked or "***" in masked


def test_mask_credit_card():
    f = PiiFilter(enabled_categories=["credit_cards"])
    text = "Card: 4242 4242 4242 4242"
    masked = f.mask_text(text)
    assert "4242 4242 4242 4242" not in masked
    assert "***" in masked


def test_mask_crypto_key():
    f = PiiFilter(enabled_categories=["crypto_keys"])
    text = "Private: 0x" + "a1b2c3d4" * 8
    masked = f.mask_text(text)
    assert "a1b2c3d4" * 8 not in masked


def test_mask_password():
    f = PiiFilter(enabled_categories=["passwords"])
    text = "password: mysecret123"
    masked = f.mask_text(text)
    assert "mysecret123" not in masked


def test_no_mask_when_disabled():
    f = PiiFilter(enabled_categories=[])
    text = "sk-1234567890abcdef"
    masked = f.mask_text(text)
    assert masked == text


def test_whitelist_app():
    f = PiiFilter(whitelist_apps=["Terminal"])
    text = "sk-1234567890abcdef1234567890abcdef"
    masked = f.mask_text(text, app_name="Terminal")
    assert masked == text  # not masked because whitelisted


def test_whitelist_no_match():
    f = PiiFilter(whitelist_apps=["Terminal"])
    text = "sk-1234567890abcdef1234567890abcdef"
    masked = f.mask_text(text, app_name="Chrome")
    assert masked != text  # masked because not whitelisted


def test_mask_elements():
    f = PiiFilter()
    elements = [
        {"text": "sk-abcdef1234567890abcdef", "x": 10, "y": 20, "w": 100, "h": 15},
        {"text": "Hello World", "x": 10, "y": 40, "w": 100, "h": 15},
    ]
    masked = f.mask_elements(elements)
    assert masked[0]["text"] != "sk-abcdef1234567890abcdef"
    assert masked[1]["text"] == "Hello World"
    assert masked[0]["x"] == 10  # coordinates preserved


def test_mask_bearer_token():
    f = PiiFilter()
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
    masked = f.mask_text(text)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in masked


def test_empty_text():
    f = PiiFilter()
    assert f.mask_text("") == ""
    assert f.mask_text("normal text no secrets") == "normal text no secrets"


def test_custom_patterns():
    f = PiiFilter(
        enabled_categories=["custom"],
        custom_patterns={"custom": [r"(SECRET_[A-Z0-9]{10,})"]}
    )
    text = "Value: SECRET_ABCDEF123456"
    masked = f.mask_text(text)
    assert "SECRET_ABCDEF123456" not in masked
