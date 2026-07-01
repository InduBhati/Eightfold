from pipeline.normalizers import (
    normalize_phone,
    normalize_email,
    normalize_skill,
    normalize_name
)

def test_phone_valid_e164():
    """Verify phone normalization for valid E164 input."""
    assert normalize_phone("+14155552671") == "+14155552671"

def test_phone_no_country_code():
    """Verify phone normalization for US number without country code."""
    assert normalize_phone("4155552671") == "+14155552671"

def test_phone_garbage():
    """Verify phone normalization returns None on invalid inputs."""
    assert normalize_phone("not-a-phone") is None

def test_email_valid():
    """Verify email normalization handles casing and surrounding whitespace."""
    assert normalize_email("  User@GMAIL.COM  ") == "user@gmail.com"

def test_email_invalid():
    """Verify email normalization returns None on invalid emails."""
    assert normalize_email("notanemail") is None

def test_skill_alias_reactjs():
    """Verify skill normalization maps ReactJS alias."""
    assert normalize_skill("ReactJS") == "react"

def test_skill_alias_nodejs():
    """Verify skill normalization maps node.js alias."""
    assert normalize_skill("node.js") == "nodejs"

def test_skill_passthrough():
    """Verify skill normalization passes unaliased skills through."""
    assert normalize_skill("postgresql") == "postgresql"

def test_normalize_name():
    """Verify name normalization title-cases and collapses whitespace."""
    assert normalize_name("  john   doe ") == "John Doe"
