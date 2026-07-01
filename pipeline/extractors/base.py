import functools
import logging
from typing import List, Callable, Any
from models.raw import RawSource, RawCandidateRecord

logger = logging.getLogger(__name__)

def safe_extract(func: Callable[[RawSource], List[RawCandidateRecord]]) -> Callable[[RawSource], List[RawCandidateRecord]]:
    """Decorator to catch exceptions during extraction, log error with file path, and return empty list."""
    @functools.wraps(func)
    def wrapper(source: RawSource, *args: Any, **kwargs: Any) -> List[RawCandidateRecord]:
        try:
            return func(source, *args, **kwargs)
        except Exception as e:
            logger.error("Failed to extract data from %s: %s", source.path, e)
            return []
    return wrapper
