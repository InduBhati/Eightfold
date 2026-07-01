import datetime
import logging
import re
import string
from typing import Optional

logger = logging.getLogger(__name__)

def normalize_phone(raw: str) -> Optional[str]:
    """Normalize a phone number to E.164 format. Returns None if invalid."""
    if not raw:
        return None
    try:
        import phonenumbers
        parsed = phonenumbers.parse(raw.strip(), "US")
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        else:
            logger.warning("Invalid phone number parsed: %s", raw)
            return None
    except Exception as e:
        logger.warning("Failed to parse phone number '%s': %s", raw, e)
        return None

def normalize_email(raw: str) -> Optional[str]:
    """Normalize and validate an email address. Returns None if invalid."""
    if not raw:
        return None
    email_clean = raw.strip().lower()
    if re.match(r'^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$', email_clean):
        return email_clean
    return None

def normalize_date(raw: str) -> Optional[str]:
    """Normalize date strings to YYYY-MM format."""
    if not raw:
        return None
    raw_clean = raw.strip()
    
    # Format YYYY-MM-DD
    try:
        dt = datetime.datetime.strptime(raw_clean, "%Y-%m-%d")
        return dt.strftime("%Y-%m")
    except ValueError:
        pass

    # Format YYYY-MM
    try:
        dt = datetime.datetime.strptime(raw_clean, "%Y-%m")
        return dt.strftime("%Y-%m")
    except ValueError:
        pass

    # Format MM/YYYY
    try:
        dt = datetime.datetime.strptime(raw_clean, "%m/%Y")
        return dt.strftime("%Y-%m")
    except ValueError:
        pass

    # Format Month YYYY or Mon YYYY
    for fmt in ["%B %Y", "%b %Y"]:
        try:
            dt = datetime.datetime.strptime(raw_clean, fmt)
            return dt.strftime("%Y-%m")
        except ValueError:
            pass

    # Format YYYY (year-only -> YYYY-01)
    try:
        dt = datetime.datetime.strptime(raw_clean, "%Y")
        return dt.strftime("%Y-01")
    except ValueError:
        pass

    return None

def normalize_country(raw: str) -> Optional[str]:
    """Map country names to 2-letter codes. Returns None if not mapped."""
    if not raw:
        return None
    raw_clean = raw.strip().lower()
    mapping = {
        "india": "IN",
        "united states": "US",
        "usa": "US",
        "us": "US",
        "uk": "GB",
        "united kingdom": "GB",
        "great britain": "GB",
        "canada": "CA",
        "germany": "DE",
        "france": "FR",
        "australia": "AU"
    }
    return mapping.get(raw_clean, None)

def normalize_skill(raw: str) -> str:
    """Normalize skill name with alias lookup and lowercase stripping."""
    raw_clean = raw.strip().lower()
    alias_map = {
        "js": "javascript",
        "reactjs": "react",
        "react.js": "react",
        "node.js": "nodejs",
        "node": "nodejs",
        "golang": "go",
        "ml": "machine-learning",
        "ai": "machine-learning",
        "c++": "cpp",
        "postgres": "postgresql",
        "mongo": "mongodb",
        "k8s": "kubernetes",
        "tf": "tensorflow",
        "py": "python"
    }
    return alias_map.get(raw_clean, raw_clean)

def normalize_name(raw: str) -> str:
    """Normalize candidate name by title-casing, collapsing spaces, and stripping punctuation."""
    if not raw:
        return ""
    text = raw.strip()
    text = text.strip(string.punctuation)
    text = " ".join(text.split())
    return text.title()
