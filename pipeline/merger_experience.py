from typing import List, Tuple, Optional
from models.raw import RawCandidateRecord
from models.canonical import Experience
from pipeline.normalizers import normalize_name, normalize_date

def get_source_weight(source_type: str) -> float:
    """Return the precedence weight of a source type."""
    weights = {"csv": 0.90, "notes": 0.60}
    return weights.get(source_type.lower(), 0.0)

def get_record_experiences(rec: RawCandidateRecord) -> List[dict]:
    """Retrieve or construct experience items from a raw candidate record."""
    rec_exp = getattr(rec, "experience", [])
    if not rec_exp and (rec.current_company or rec.title):
        return [{
            "company": rec.current_company or "",
            "title": rec.title or "",
            "start": None,
            "end": None,
            "summary": None
        }]
    
    output = []
    for exp in rec_exp:
        if isinstance(exp, dict):
            output.append(exp)
        else:
            output.append({
                "company": exp.company,
                "title": exp.title,
                "start": exp.start,
                "end": exp.end,
                "summary": exp.summary
            })
    return output

def merge_experiences(sorted_cluster: List[RawCandidateRecord]) -> Tuple[List[Experience], Optional[str], float]:
    """Merge work history records by company and title keys, filling gaps from lower weights."""
    experience_groups = {}
    experience_source = None
    experience_weight = 0.0
    
    for rec in sorted_cluster:
        rec_exp = get_record_experiences(rec)
        for exp in rec_exp:
            company = exp.get("company", "")
            title = exp.get("title", "")
            key = (normalize_name(company), normalize_name(title))
            if key not in experience_groups:
                experience_groups[key] = []
            experience_groups[key].append((company, title, exp.get("start"), exp.get("end"), exp.get("summary"), rec))
            
    merged_experiences: List[Experience] = []
    
    for key, exp_list in experience_groups.items():
        exp_list_sorted = sorted(exp_list, key=lambda x: -get_source_weight(x[5].source_type))
        base_company, base_title, base_start, base_end, base_summary, base_rec = exp_list_sorted[0]
        
        merged_start = base_start
        merged_end = base_end
        merged_summary = base_summary
        
        for other in exp_list_sorted[1:]:
            if not merged_start and other[2]:
                merged_start = other[2]
            if not merged_end and other[3]:
                merged_end = other[3]
            if not merged_summary and other[4]:
                merged_summary = other[4]
                
        norm_start = normalize_date(merged_start) if merged_start else None
        norm_end = normalize_date(merged_end) if merged_end else None
        
        merged_experiences.append(Experience(
            company=base_company,
            title=base_title,
            start=norm_start,
            end=norm_end,
            summary=merged_summary
        ))
        
        if not experience_source:
            experience_source = base_rec.source_path
            experience_weight = get_source_weight(base_rec.source_type)
            
    merged_experiences.sort(key=lambda e: (e.company, e.title))
    return merged_experiences, experience_source, experience_weight
