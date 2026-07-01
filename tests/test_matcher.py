from models.raw import RawCandidateRecord
from pipeline.matcher import match_candidates, generate_candidate_id

def test_shared_email_clusters_together():
    """Verify records sharing normalized email cluster together."""
    r1 = RawCandidateRecord(source_path="c1.csv", source_type="csv", full_name="John Doe", email="john@gmail.com")
    r2 = RawCandidateRecord(source_path="n1.txt", source_type="notes", full_name="Jonny Doe", email="john@gmail.com")
    clusters = match_candidates([r1, r2])
    assert len(clusters) == 1
    assert len(clusters[0]) == 2

def test_different_emails_stay_separate():
    """Verify records with different emails remain separate."""
    r1 = RawCandidateRecord(source_path="c1.csv", source_type="csv", full_name="John Doe", email="john@gmail.com")
    r2 = RawCandidateRecord(source_path="c2.csv", source_type="csv", full_name="John Doe", email="jane@gmail.com")
    clusters = match_candidates([r1, r2])
    assert len(clusters) == 2

def test_secondary_match_requires_both_name_and_phone():
    """Verify name similarity >= 85 and phone matches clusters them."""
    r1 = RawCandidateRecord(source_path="c1.csv", source_type="csv", full_name="John Doe", phone="4155552671")
    r2 = RawCandidateRecord(source_path="c2.csv", source_type="csv", full_name="Jon Doe", phone="4155552671")
    clusters = match_candidates([r1, r2])
    assert len(clusters) == 1

    r3 = RawCandidateRecord(source_path="c1.csv", source_type="csv", full_name="John Doe", phone="4155552671")
    r4 = RawCandidateRecord(source_path="c2.csv", source_type="csv", full_name="Alice Smith", phone="4155552671")
    clusters_diff = match_candidates([r3, r4])
    assert len(clusters_diff) == 2

def test_candidate_id_deterministic():
    """Verify that generate_candidate_id is deterministic."""
    r1 = RawCandidateRecord(source_path="c1.csv", source_type="csv", full_name="John Doe", email="john@gmail.com")
    r2 = RawCandidateRecord(source_path="n1.txt", source_type="notes", full_name="Jonny Doe", email="john@gmail.com")
    cluster = [r1, r2]
    
    id1 = generate_candidate_id(cluster)
    id2 = generate_candidate_id(cluster)
    assert id1 == id2
    assert isinstance(id1, str)

def test_no_email_uses_name_company_seed():
    """Verify that missing emails seed the deterministic UUID via name and company."""
    r = RawCandidateRecord(source_path="c1.csv", source_type="csv", full_name="John Doe", current_company="Google")
    cid = generate_candidate_id([r])
    
    import uuid
    expected = str(uuid.uuid5(uuid.NAMESPACE_URL, "John Doe|Google"))
    assert cid == expected
