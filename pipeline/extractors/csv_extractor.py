import csv
import io
from typing import List
from models.raw import RawSource, RawCandidateRecord
from pipeline.extractors.base import safe_extract

@safe_extract
def extract_csv(source: RawSource) -> List[RawCandidateRecord]:
    """Extract RawCandidateRecord list from a CSV source."""
    records = []
    f = io.StringIO(source.payload)
    reader = csv.DictReader(f)
    
    for row in reader:
        # Clean and strip all values
        cleaned_row = {}
        for k, v in row.items():
            if k is not None:
                cleaned_key = k.strip()
                cleaned_val = v.strip() if v else ""
                cleaned_row[cleaned_key] = cleaned_val

        name = cleaned_row.get("name", "")
        email = cleaned_row.get("email", "")
        phone = cleaned_row.get("phone", "")
        current_company = cleaned_row.get("current_company", "")
        title = cleaned_row.get("title", "")

        # Skip rows where name AND email are both empty (Edge Case 5/6 helper)
        if not name and not email:
            continue

        record = RawCandidateRecord(
            source_path=source.path,
            source_type=source.type,
            full_name=name if name else None,
            email=email if email else None,
            phone=phone if phone else None,
            current_company=current_company if current_company else None,
            title=title if title else None,
            raw_text=str(cleaned_row)
        )
        records.append(record)

    return records
