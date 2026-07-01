import datetime
import logging
import os
from typing import List
from models.raw import RawSource

logger = logging.getLogger(__name__)

def load_source_file(path: str) -> List[RawSource]:
    """Load a single file from disk and return its RawSource if successful."""
    if not os.path.exists(path):
        logger.warning("File not found: %s", path)
        return []
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".csv":
            source_type = "csv"
        elif ext == ".txt":
            source_type = "notes"
        else:
            logger.warning("Unsupported file format: %s", path)
            return []
            
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        loaded_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return [RawSource(type=source_type, payload=content, path=path, loaded_at=loaded_at)]
    except Exception as e:
        logger.warning("Failed to load file %s: %s", path, e)
        return []

def load_sources(paths: List[str]) -> List[RawSource]:
    """Load all specified file paths, ignoring individual failures."""
    sources = []
    for path in paths:
        sources.extend(load_source_file(path))
    return sources
