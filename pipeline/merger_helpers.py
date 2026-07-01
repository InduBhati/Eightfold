import logging
from typing import List, Optional, Tuple, Any
from models.raw import RawCandidateRecord
from models.canonical import Skill, Education, Location, Links
from pipeline.normalizers import (
    normalize_email, normalize_phone, normalize_name, normalize_country, normalize_skill
)

logger = logging.getLogger(__name__)

def get_source_weight(source_type: str) -> float:
    """Return the precedence weight of a source type."""
    weights = {"csv": 0.90, "notes": 0.60}
    return weights.get(source_type.lower(), 0.0)

def merge_scalar_field(field_name: str, sorted_cluster: List[RawCandidateRecord]) -> Tuple[Optional[Any], Optional[str], float]:
    """Merge scalar fields, logging conflicts if values differ."""
    val = None
    val_source = None
    val_weight = 0.0
    for rec in sorted_cluster:
        rec_val = getattr(rec, field_name, None)
        if rec_val:
            if field_name == "full_name":
                rec_val = normalize_name(str(rec_val))
            if not val:
                val = rec_val
                val_source = rec.source_path
                val_weight = get_source_weight(rec.source_type)
            elif val != rec_val:
                logger.warning("Conflict for field '%s': '%s' vs '%s'", field_name, val, rec_val)
    return val, val_source, val_weight

def merge_location(sorted_cluster: List[RawCandidateRecord]) -> Tuple[Optional[Location], Optional[str], float]:
    """Merge location data across sources."""
    location = None
    location_source = None
    location_weight = 0.0
    for rec in sorted_cluster:
        rec_loc = getattr(rec, "location", None)
        if rec_loc:
            if isinstance(rec_loc, dict):
                rec_loc = Location(
                    city=rec_loc.get("city"),
                    region=rec_loc.get("region"),
                    country=normalize_country(rec_loc.get("country"))
                )
            if not location:
                location = rec_loc
                location_source = rec.source_path
                location_weight = get_source_weight(rec.source_type)
            elif location != rec_loc:
                logger.warning("Conflict for field 'location': '%s' vs '%s'", location, rec_loc)
    return location, location_source, location_weight

def merge_emails(sorted_cluster: List[RawCandidateRecord]) -> Tuple[List[str], Optional[str], float]:
    """Union and normalize candidate emails."""
    seen = set()
    merged = []
    source = None
    weight = 0.0
    for rec in sorted_cluster:
        rec_emails = [rec.email] if rec.email else []
        for email in rec_emails:
            norm = normalize_email(email)
            if norm and norm not in seen:
                seen.add(norm)
                merged.append(norm)
                if not source:
                    source = rec.source_path
                    weight = get_source_weight(rec.source_type)
    merged.sort()
    return merged, source, weight

def merge_phones(sorted_cluster: List[RawCandidateRecord]) -> Tuple[List[str], Optional[str], float]:
    """Union and normalize candidate phone numbers."""
    seen = set()
    merged = []
    source = None
    weight = 0.0
    for rec in sorted_cluster:
        rec_phones = [rec.phone] if rec.phone else []
        for phone in rec_phones:
            norm = normalize_phone(phone)
            if norm and norm not in seen:
                seen.add(norm)
                merged.append(norm)
                if not source:
                    source = rec.source_path
                    weight = get_source_weight(rec.source_type)
    merged.sort()
    return merged, source, weight

def merge_links(sorted_cluster: List[RawCandidateRecord]) -> Tuple[Links, Optional[str], float]:
    """Union and prioritize candidate web link fields."""
    linkedin, github, portfolio = None, None, None
    seen_other = set()
    other_links = []
    source = None
    weight = 0.0
    for rec in sorted_cluster:
        rec_li = getattr(rec, "linkedin", None)
        rec_gh = getattr(rec, "github", None)
        rec_port = getattr(rec, "portfolio", None)
        rec_other = getattr(rec, "other_links", [])
        if rec_li or rec_gh or rec_port or rec_other:
            if not source:
                source = rec.source_path
                weight = get_source_weight(rec.source_type)
            if rec_li and not linkedin:
                linkedin = rec_li
            if rec_gh and not github:
                github = rec_gh
            if rec_port and not portfolio:
                portfolio = rec_port
            for link in rec_other:
                clean = link.strip()
                if clean and clean not in seen_other:
                    seen_other.add(clean)
                    other_links.append(clean)
    other_links.sort()
    return Links(linkedin=linkedin, github=github, portfolio=portfolio, other=other_links), source, weight

def merge_skills(sorted_cluster: List[RawCandidateRecord]) -> Tuple[List[Skill], Optional[str], float]:
    """Union skills and calculate per-skill confidence scores."""
    skill_records = {}
    for rec in sorted_cluster:
        for sk in getattr(rec, "skills", []):
            norm = normalize_skill(sk)
            if norm:
                if norm not in skill_records:
                    skill_records[norm] = []
                skill_records[norm].append(rec)
    merged = []
    source = None
    weight = 0.0
    for norm, recs in skill_records.items():
        max_w = max(get_source_weight(r.source_type) for r in recs)
        count = len(recs)
        confidence = min(1.0, max_w + 0.10 * (count - 1))
        sources = sorted(list(set(r.source_path for r in recs)))
        merged.append(Skill(name=norm, confidence=round(confidence, 4), sources=sources))
        if not source:
            source = recs[0].source_path
            weight = max_w
    merged.sort(key=lambda s: s.name)
    return merged, source, weight

def merge_education(sorted_cluster: List[RawCandidateRecord]) -> Tuple[List[Education], Optional[str], float]:
    """Merge academic education history records."""
    edu_groups = {}
    source = None
    weight = 0.0
    for rec in sorted_cluster:
        for edu in getattr(rec, "education", []):
            if isinstance(edu, dict):
                inst = edu.get("institution", "")
                deg = edu.get("degree")
                fld = edu.get("field")
                ey = edu.get("end_year")
            else:
                inst = edu.institution
                deg = edu.degree
                fld = edu.field
                ey = edu.end_year
            key = (normalize_name(inst), normalize_name(deg or ""))
            if key not in edu_groups:
                edu_groups[key] = []
            edu_groups[key].append((inst, deg, fld, ey, rec))
    merged = []
    for key, edu_list in edu_groups.items():
        sorted_edu = sorted(edu_list, key=lambda x: -get_source_weight(x[4].source_type))
        base_inst, base_deg, base_fld, base_ey, base_rec = sorted_edu[0]
        merged_fld, merged_ey = base_fld, base_ey
        for other in sorted_edu[1:]:
            if not merged_fld and other[2]:
                merged_fld = other[2]
            if not merged_ey and other[3]:
                merged_ey = other[3]
        merged.append(Education(institution=base_inst, degree=base_deg, field=merged_fld, end_year=merged_ey))
        if not source:
            source = base_rec.source_path
            weight = get_source_weight(base_rec.source_type)
    merged.sort(key=lambda e: (e.institution, e.degree or ""))
    return merged, source, weight
