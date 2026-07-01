import logging
import re
from typing import List, Optional
from models.raw import RawSource, RawCandidateRecord
from pipeline.extractors.base import safe_extract

logger = logging.getLogger(__name__)

def split_into_blocks(text: str) -> List[str]:
    """Split unstructured note text into individual candidate blocks."""
    lines = text.splitlines()
    blocks = []
    current_block_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check for explicit separator "---"
        if line.startswith("---") or line == "---":
            if current_block_lines:
                blocks.append("\n".join(current_block_lines))
                current_block_lines = []
            i += 1
            continue
            
        # Check for blank line followed by a name-like line
        if not line:
            # Look ahead for the next non-empty line
            next_idx = i + 1
            while next_idx < len(lines) and not lines[next_idx].strip():
                next_idx += 1
            
            if next_idx < len(lines):
                next_line = lines[next_idx].strip()
                # Name-like line: no @, no digits, and not empty
                has_at = "@" in next_line
                has_digit = any(c.isdigit() for c in next_line)
                is_name_like = not has_at and not has_digit and len(next_line) > 0
                
                if is_name_like:
                    if current_block_lines:
                        blocks.append("\n".join(current_block_lines))
                        current_block_lines = []
                    i = next_idx
                    current_block_lines.append(lines[i])
                    i += 1
                    continue
        
        current_block_lines.append(lines[i])
        i += 1
        
    if current_block_lines:
        blocks.append("\n".join(current_block_lines))
        
    return [b.strip() for b in blocks if b.strip()]

def extract_name(block_text: str) -> Optional[str]:
    """Extract the first non-empty name-like line from a block."""
    for line in block_text.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue
        if "@" in line_clean:
            continue
        if any(c.isdigit() for c in line_clean):
            continue
        # Skip lines that look like standard key-value headers
        lower_line = line_clean.lower()
        if lower_line.startswith(("skills:", "tech:", "stack:", "linkedin:", "github:", "portfolio:", "phone:", "email:")):
            continue
        return line_clean
    return None

def parse_company_line(block_text: str) -> tuple[Optional[str], Optional[str]]:
    """Scan lines for role and company combinations."""
    for line in block_text.splitlines():
        line_clean = line.strip()
        # Skip if the line contains a valid email to prevent matching email '@'
        if "@" in line_clean and re.search(r'[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}', line_clean):
            continue
        if line_clean.lower().startswith(("email:", "phone:", "skills:", "tech:", "stack:", "linkedin:", "github:", "portfolio:")):
            continue
            
        # Look for company separators: "currently at", "works at", "at ", "@ "
        for pattern in ["currently at", "works at", "at", "@"]:
            if pattern == "@":
                # Match @ with optional surrounding whitespace but ensure it's a separator
                match = re.search(r'\s+@\s*|@\s+', line_clean)
            elif pattern == "at":
                # Match "at" as a full word
                match = re.search(r'\bat\s+', line_clean, re.IGNORECASE)
            else:
                match = re.search(r'\b' + re.escape(pattern) + r'\b', line_clean, re.IGNORECASE)
                
            if match:
                start, end = match.span()
                role = line_clean[:start].strip()
                company = line_clean[end:].strip()
                # Clean up punctuation and return
                return (role if role else None, company if company else None)
    return None, None

def extract_urls(block_text: str) -> tuple[Optional[str], Optional[str], List[str]]:
    """Extract LinkedIn, GitHub, and other links from block."""
    linkedin_pattern = r'linkedin\.com/in/[\w-]+'
    github_pattern = r'github\.com/[\w-]+'
    
    linkedin_matches = re.findall(linkedin_pattern, block_text, re.IGNORECASE)
    github_matches = re.findall(github_pattern, block_text, re.IGNORECASE)
    
    # Extract any URL containing https:// or http:// as candidates for other links
    all_urls = re.findall(r'https?://[^\s]+', block_text, re.IGNORECASE)
    other_links = []
    for url in all_urls:
        url_clean = url.strip(".,()[]{}<>\"'")
        if "linkedin.com" in url_clean.lower() or "github.com" in url_clean.lower():
            continue
        other_links.append(url_clean)
        
    linkedin = linkedin_matches[0] if linkedin_matches else None
    github = github_matches[0] if github_matches else None
    return linkedin, github, other_links

def extract_skills(block_text: str) -> List[str]:
    """Extract comma-separated skills from stack lines."""
    skills = []
    for line in block_text.splitlines():
        line_clean = line.strip()
        lower_line = line_clean.lower()
        for prefix in ["skills:", "tech:", "stack:"]:
            if prefix in lower_line:
                idx = lower_line.index(prefix)
                skills_part = line_clean[idx + len(prefix):].strip()
                if skills_part:
                    parts = [s.strip() for s in skills_part.split(",") if s.strip()]
                    skills.extend(parts)
                break
    return skills

@safe_extract
def extract_notes(source: RawSource) -> List[RawCandidateRecord]:
    """Extract RawCandidateRecord list from an unstructured notes text file."""
    blocks = split_into_blocks(source.payload)
    if not blocks:
        logger.warning("No candidate blocks detected in notes file: %s", source.path)
        return []
        
    records = []
    for block in blocks:
        name = extract_name(block)
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}', block)
        email = email_match.group(0) if email_match else None
        
        phone_match = re.search(r'[\+\d][\d\s\-().]{7,}\d', block)
        phone = phone_match.group(0) if phone_match else None
        
        skills = extract_skills(block)
        role, company = parse_company_line(block)
        linkedin, github, other_links = extract_urls(block)
        
        # Skip if name and email are both empty
        if not name and not email:
            continue
            
        record = RawCandidateRecord(
            source_path=source.path,
            source_type=source.type,
            full_name=name,
            email=email,
            phone=phone,
            current_company=company,
            title=role,
            skills=skills,
            linkedin=linkedin,
            github=github,
            other_links=other_links,
            raw_text=block
        )
        records.append(record)
        
    return records
