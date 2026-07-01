from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class RawSource:
    """Represents a source file loaded from disk."""
    type: str  # "csv" or "notes"
    payload: str
    path: str
    loaded_at: str

@dataclass
class RawCandidateRecord:
    """Represents an extracted candidate record before normalization."""
    source_path: str
    source_type: str  # "csv" or "notes"
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    current_company: Optional[str] = None
    title: Optional[str] = None
    headline: Optional[str] = None
    years_experience: Optional[float] = None
    skills: List[str] = field(default_factory=list)
    linkedin: Optional[str] = None
    github: Optional[str] = None
    other_links: List[str] = field(default_factory=list)
    raw_text: Optional[str] = None
