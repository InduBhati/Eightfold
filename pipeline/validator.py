import logging
from typing import Any, Dict, Optional
from jsonschema import Draft7Validator

logger = logging.getLogger(__name__)

DEFAULT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "candidate_id": {"type": "string"},
        "full_name": {"type": ["string", "null"]},
        "emails": {"type": "array", "items": {"type": "string"}},
        "phones": {"type": "array", "items": {"type": "string"}},
        "location": {
            "type": ["object", "null"],
            "properties": {
                "city": {"type": ["string", "null"]},
                "region": {"type": ["string", "null"]},
                "country": {"type": ["string", "null"]}
            }
        },
        "links": {
            "type": ["object", "null"],
            "properties": {
                "linkedin": {"type": ["string", "null"]},
                "github": {"type": ["string", "null"]},
                "portfolio": {"type": ["string", "null"]},
                "other": {"type": "array", "items": {"type": "string"}}
            }
        },
        "headline": {"type": ["string", "null"]},
        "years_experience": {"type": ["number", "null"]},
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "confidence": {"type": "number"},
                    "sources": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["name", "confidence"]
            }
        },
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "title": {"type": "string"},
                    "start": {"type": ["string", "null"]},
                    "end": {"type": ["string", "null"]},
                    "summary": {"type": ["string", "null"]}
                },
                "required": ["company", "title"]
            }
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "institution": {"type": "string"},
                    "degree": {"type": ["string", "null"]},
                    "field": {"type": ["string", "null"]},
                    "end_year": {"type": ["integer", "null"]}
                },
                "required": ["institution"]
            }
        },
        "provenance": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "source": {"type": "string"},
                    "method": {"type": "string"}
                },
                "required": ["field", "source", "method"]
            }
        },
        "overall_confidence": {"type": "number"}
    },
    "required": ["candidate_id", "overall_confidence"]
}

def build_schema_from_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Dynamically construct a JSON Schema from a project configuration definition."""
    fields = config.get("fields", [])
    properties: Dict[str, Any] = {}
    required = []
    
    for f in fields:
        path = f.get("path")
        f_type = f.get("type", "string")
        is_required = f.get("required", False)
        
        if not path:
            continue
            
        if is_required:
            properties[path] = {"type": f_type}
            required.append(path)
        else:
            properties[path] = {"type": [f_type, "null"]}
            
    if config.get("include_confidence", False):
        properties["overall_confidence"] = {"type": "number"}
        
    if config.get("include_provenance", False):
        properties["provenance"] = {"type": "array"}
        
    return {
        "type": "object",
        "properties": properties,
        "required": required
    }

def validate_projected(output_dict: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Validate a projected profile structure, appending validation error lists and penalizing confidence if invalid."""
    schema = build_schema_from_config(config) if config and config.get("fields") else DEFAULT_SCHEMA
    
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(output_dict))
    
    if errors:
        for err in errors:
            field_name = list(err.path)[0] if err.path else "unknown_field"
            logger.error("Validation error for field '%s': %s", field_name, err.message)
            
            if "validation_errors" not in output_dict:
                output_dict["validation_errors"] = []
            output_dict["validation_errors"].append(err.message)
            
        # Halve the overall confidence score on validation failure
        if "overall_confidence" in output_dict:
            output_dict["overall_confidence"] = round(output_dict["overall_confidence"] * 0.5, 4)
            
    return output_dict
