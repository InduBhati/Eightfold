import pytest
from models.canonical import CandidateProfile, Location, Links, Skill
from pipeline.projector import project_profile

@pytest.fixture
def sample_profile():
    """Fixture providing a filled canonical CandidateProfile for projection testing."""
    return CandidateProfile(
        candidate_id="uuid-1234",
        full_name="John Doe",
        emails=["john@gmail.com", "j.doe@gmail.com"],
        phones=["+14155552671"],
        location=Location(city="San Francisco", region="CA", country="US"),
        links=Links(linkedin="linkedin.com/in/johndoe", github="github.com/johndoe", other=[]),
        skills=[
            Skill(name="python", confidence=0.9, sources=["c.csv"]),
            Skill(name="go", confidence=0.6, sources=["n.txt"])
        ],
        overall_confidence=0.9
    )

def test_rename_via_from_key(sample_profile):
    """Verify that using the 'from' key correctly maps and renames fields."""
    config = {
        "fields": [
            {"path": "name", "from": "full_name", "type": "string"}
        ]
    }
    projected = project_profile(sample_profile, config)
    assert projected.get("name") == "John Doe"
    assert "full_name" not in projected

def test_array_index_path(sample_profile):
    """Verify list index access works (e.g. emails[0])."""
    config = {
        "fields": [
            {"path": "primary_email", "from": "emails[0]", "type": "string"}
        ]
    }
    projected = project_profile(sample_profile, config)
    assert projected.get("primary_email") == "john@gmail.com"

def test_array_pluck_path(sample_profile):
    """Verify attribute plucking over list objects (e.g. skills[].name)."""
    config = {
        "fields": [
            {"path": "skill_names", "from": "skills[].name", "type": "array"}
        ]
    }
    projected = project_profile(sample_profile, config)
    assert sorted(projected.get("skill_names", [])) == ["go", "python"]

def test_on_missing_null(sample_profile):
    """Verify missing fields evaluate to null if on_missing is set to null."""
    config = {
        "fields": [
            {"path": "headline", "type": "string"}
        ],
        "on_missing": "null"
    }
    projected = project_profile(sample_profile, config)
    assert "headline" in projected
    assert projected["headline"] is None

def test_on_missing_omit(sample_profile):
    """Verify missing fields are excluded if on_missing is set to omit."""
    config = {
        "fields": [
            {"path": "headline", "type": "string"}
        ],
        "on_missing": "omit"
    }
    projected = project_profile(sample_profile, config)
    assert "headline" not in projected

def test_on_missing_error(sample_profile):
    """Verify missing fields raise ValueError if on_missing is set to error."""
    config = {
        "fields": [
            {"path": "headline", "type": "string"}
        ],
        "on_missing": "error"
    }
    with pytest.raises(ValueError) as exc:
        project_profile(sample_profile, config)
    assert "Missing required field" in str(exc.value)

def test_empty_config_returns_full_profile(sample_profile):
    """Verify empty/missing config outputs the raw canonical profile dict."""
    projected = project_profile(sample_profile, None)
    assert projected["candidate_id"] == "uuid-1234"
    assert projected["full_name"] == "John Doe"

def test_nested_path_access(sample_profile):
    """Verify nested key access (e.g. location.city) works correctly."""
    config = {
        "fields": [
            {"path": "city", "from": "location.city", "type": "string"}
        ]
    }
    projected = project_profile(sample_profile, config)
    assert projected.get("city") == "San Francisco"
