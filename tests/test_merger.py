import logging
from models.raw import RawCandidateRecord
from pipeline.merger import merge_cluster

def test_csv_wins_over_notes_on_scalar():
    """Verify that CSV source values override notes values on scalar fields due to higher weight."""
    r1 = RawCandidateRecord(source_path="c1.csv", source_type="csv", full_name="John Doe", headline="Senior Software Engineer", years_experience=5.0)
    r2 = RawCandidateRecord(source_path="n1.txt", source_type="notes", full_name="Jonny Doe", headline="Software Engineer", years_experience=3.0)
    profile = merge_cluster("test-id", [r1, r2])
    assert profile.full_name == "John Doe"
    assert profile.headline == "Senior Software Engineer"
    assert profile.years_experience == 5.0

def test_list_fields_are_unioned_and_deduped():
    """Verify list fields are merged, normalized, and unique."""
    r1 = RawCandidateRecord(source_path="c1.csv", source_type="csv", email="john@gmail.com", phone="4155552671")
    r2 = RawCandidateRecord(source_path="n1.txt", source_type="notes", email="john.doe@gmail.com", phone="415-555-2671")
    profile = merge_cluster("test-id", [r1, r2])
    
    assert len(profile.phones) == 1
    assert profile.phones[0] == "+14155552671"
    assert len(profile.emails) == 2
    assert profile.emails == ["john.doe@gmail.com", "john@gmail.com"]

def test_skill_confidence_increases_with_sources():
    """Verify that skill confidence increases when mentioned by more sources."""
    r1 = RawCandidateRecord(source_path="c1.csv", source_type="csv", skills=["python", "java"])
    r2 = RawCandidateRecord(source_path="n1.txt", source_type="notes", skills=["python", "c++"])
    profile = merge_cluster("test-id", [r1, r2])
    
    python_skill = next(s for s in profile.skills if s.name == "python")
    assert python_skill.confidence == 1.0
    
    java_skill = next(s for s in profile.skills if s.name == "java")
    assert java_skill.confidence == 0.90

def test_overall_confidence_between_0_and_1():
    """Verify calculated overall confidence is normalized inside [0, 1]."""
    r1 = RawCandidateRecord(source_path="c1.csv", source_type="csv", full_name="John Doe", email="john@gmail.com")
    profile = merge_cluster("test-id", [r1])
    assert 0.0 <= profile.overall_confidence <= 1.0

def test_provenance_populated_for_every_field():
    """Verify that provenance list tracks all populated fields."""
    r1 = RawCandidateRecord(source_path="c1.csv", source_type="csv", full_name="John Doe", email="john@gmail.com", phone="4155552671")
    profile = merge_cluster("test-id", [r1])
    
    fields = [p.field for p in profile.provenance]
    assert "full_name" in fields
    assert "emails" in fields
    assert "phones" in fields

def test_conflicting_names_logged(caplog):
    """Verify that name merge conflicts are logged via warning level."""
    r1 = RawCandidateRecord(source_path="c1.csv", source_type="csv", full_name="John Doe")
    r2 = RawCandidateRecord(source_path="n1.txt", source_type="notes", full_name="Jonny Doe")
    with caplog.at_level(logging.WARNING):
        merge_cluster("test-id", [r1, r2])
    assert any("Conflict for field 'full_name'" in record.message for record in caplog.records)
