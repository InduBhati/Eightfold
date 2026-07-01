import logging
import re
from typing import Any, Dict, List, Optional
from models.canonical import CandidateProfile
from pipeline.normalizers import normalize_phone, normalize_skill

logger = logging.getLogger(__name__)

def resolve_path(data: Any, path: str) -> Any:
    """Resolve a dot-notated and array-indexed path on nested dictionaries."""
    if not path:
        return data
        
    parts = path.split('.')
    current = data
    
    for i, part in enumerate(parts):
        match = re.match(r'^(\w+)(?:\[(\d*)\])?$', part)
        if not match:
            # If part doesn't match standard name[index] or name[], try direct key lookup
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
            continue
            
        field, index_str = match.groups()
        
        # Access field
        if isinstance(current, dict) and field in current:
            current = current[field]
        else:
            return None
            
        # Handle list indexing or plucking
        if '[' in part:
            if not isinstance(current, list):
                return None
            if index_str == '':
                # Pluck list attributes (e.g., skills[].name)
                remaining_path = ".".join(parts[i+1:])
                plucked = []
                for item in current:
                    val = resolve_path(item, remaining_path)
                    if val is not None:
                        plucked.append(val)
                return plucked
            else:
                # Specific index access (e.g., emails[0])
                idx = int(index_str)
                if idx < len(current):
                    current = current[idx]
                else:
                    return None
                    
    return current

def project_profile(profile: CandidateProfile, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Project a canonical CandidateProfile into the dictionary shape configured by runtime settings."""
    profile_dict = profile.model_dump()
    
    if not config or not config.get("fields"):
        return profile_dict
        
    output: Dict[str, Any] = {}
    on_missing = config.get("on_missing", "null").lower()
    fields = config.get("fields", [])
    
    for f_conf in fields:
        out_key = f_conf.get("path")
        source_path = f_conf.get("from", out_key)
        
        if not out_key:
            continue
            
        val = resolve_path(profile_dict, source_path)
        
        # Apply normalization if specified
        norm_type = f_conf.get("normalize")
        if val is not None:
            if norm_type == "E164":
                val = normalize_phone(str(val))
            elif norm_type == "canonical":
                if isinstance(val, list):
                    val = [normalize_skill(str(x)) for x in val]
                else:
                    val = normalize_skill(str(val))
                    
        # Apply on_missing policy if the value is missing/null
        if val is None:
            if on_missing == "omit":
                continue
            elif on_missing == "error":
                raise ValueError(f"Missing required field: {source_path}")
            else:  # "null"
                output[out_key] = None
        else:
            output[out_key] = val
            
    # Include confidence and/or provenance if requested
    if config.get("include_confidence", False):
        output["overall_confidence"] = profile_dict.get("overall_confidence", 0.0)
        
    if config.get("include_provenance", False):
        output["provenance"] = profile_dict.get("provenance", [])
        
    return output
