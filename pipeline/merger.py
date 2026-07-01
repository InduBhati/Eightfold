import logging
from typing import List
from models.raw import RawCandidateRecord
from models.canonical import CandidateProfile, Provenance
from pipeline.merger_experience import merge_experiences
from pipeline.merger_helpers import (
    get_source_weight,
    merge_scalar_field,
    merge_location,
    merge_emails,
    merge_phones,
    merge_links,
    merge_skills,
    merge_education
)

logger = logging.getLogger(__name__)

def merge_cluster(candidate_id: str, cluster: List[RawCandidateRecord]) -> CandidateProfile:
    """Merge a cluster of raw records into a single canonical CandidateProfile."""
    sorted_cluster = sorted(
        cluster,
        key=lambda r: (-get_source_weight(r.source_type), r.source_path, r.raw_text or "")
    )
    
    provenance_list: List[Provenance] = []
    
    # 1. full_name
    full_name, fn_src, fn_weight = merge_scalar_field("full_name", sorted_cluster)
    if full_name and fn_src:
        provenance_list.append(Provenance(field="full_name", source=fn_src, method="normalized"))
        
    # 2. emails
    emails, e_src, e_weight = merge_emails(sorted_cluster)
    if emails and e_src:
        provenance_list.append(Provenance(field="emails", source=e_src, method="normalized"))
        
    # 3. phones
    phones, p_src, p_weight = merge_phones(sorted_cluster)
    if phones and p_src:
        provenance_list.append(Provenance(field="phones", source=p_src, method="normalized"))
        
    # 4. location
    location, loc_src, loc_weight = merge_location(sorted_cluster)
    if location and loc_src:
        provenance_list.append(Provenance(field="location", source=loc_src, method="direct"))
        
    # 5. links
    links_obj, l_src, l_weight = merge_links(sorted_cluster)
    if (links_obj.linkedin or links_obj.github or links_obj.portfolio or links_obj.other) and l_src:
        method = "regex_extracted" if "notes" in l_src.lower() else "direct"
        provenance_list.append(Provenance(field="links", source=l_src, method=method))
        
    # 6. headline
    headline, hl_src, hl_weight = merge_scalar_field("headline", sorted_cluster)
    if headline and hl_src:
        provenance_list.append(Provenance(field="headline", source=hl_src, method="direct"))
        
    # 7. years_experience
    years_exp, ye_src, ye_weight = merge_scalar_field("years_experience", sorted_cluster)
    if years_exp is not None and ye_src:
        provenance_list.append(Provenance(field="years_experience", source=ye_src, method="direct"))
        
    # 8. skills
    skills, sk_src, sk_weight = merge_skills(sorted_cluster)
    if skills and sk_src:
        provenance_list.append(Provenance(field="skills", source=sk_src, method="normalized"))
        
    # 9. experience
    experiences, exp_src, exp_weight = merge_experiences(sorted_cluster)
    if experiences and exp_src:
        provenance_list.append(Provenance(field="experience", source=exp_src, method="normalized"))
        
    # 10. education
    education, edu_src, edu_weight = merge_education(sorted_cluster)
    if education and edu_src:
        provenance_list.append(Provenance(field="education", source=edu_src, method="direct"))
        
    # Sort provenance by field name
    provenance_list.sort(key=lambda p: p.field)
    
    # 11. overall_confidence calculation
    populated_fields = {}
    if full_name:
        populated_fields["full_name"] = {"weight": 2.0, "confidence": fn_weight}
    if emails:
        populated_fields["emails"] = {"weight": 2.0, "confidence": e_weight}
    if phones:
        populated_fields["phones"] = {"weight": 1.0, "confidence": p_weight}
    if location:
        populated_fields["location"] = {"weight": 1.0, "confidence": loc_weight}
    if links_obj.linkedin or links_obj.github or links_obj.portfolio or links_obj.other:
        populated_fields["links"] = {"weight": 1.0, "confidence": l_weight}
    if headline:
        populated_fields["headline"] = {"weight": 1.0, "confidence": hl_weight}
    if years_exp is not None:
        populated_fields["years_experience"] = {"weight": 1.0, "confidence": ye_weight}
    if skills:
        populated_fields["skills"] = {"weight": 1.0, "confidence": sk_weight}
    if experiences:
        populated_fields["experience"] = {"weight": 1.0, "confidence": exp_weight}
    if education:
        populated_fields["education"] = {"weight": 1.0, "confidence": edu_weight}
        
    weighted_sum = sum(info["confidence"] * info["weight"] for info in populated_fields.values())
    denominator = 4.0
    overall_confidence = min(1.0, weighted_sum / denominator)
    
    return CandidateProfile(
        candidate_id=candidate_id,
        full_name=full_name,
        emails=emails,
        phones=phones,
        location=location,
        links=links_obj,
        headline=headline,
        years_experience=years_exp,
        skills=skills,
        experience=experiences,
        education=education,
        provenance=provenance_list,
        overall_confidence=round(overall_confidence, 4)
    )
