import logging
import uuid
from collections import defaultdict
from typing import List, Dict, Set
from models.raw import RawCandidateRecord
from pipeline.normalizers import normalize_email, normalize_phone, normalize_name

logger = logging.getLogger(__name__)

class UnionFind:
    """Disjoint-set data structure with path compression and union by rank."""
    def __init__(self, size: int):
        self.parent = list(range(size))
        self.rank = [1] * size

    def find(self, i: int) -> int:
        """Find the representative of the set containing i, with path compression."""
        if self.parent[i] == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i: int, j: int) -> bool:
        """Union the sets containing i and j. Returns True if merged, False otherwise."""
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            if self.rank[root_i] > self.rank[root_j]:
                self.parent[root_j] = root_i
            elif self.rank[root_i] < self.rank[root_j]:
                self.parent[root_i] = root_j
            else:
                self.parent[root_j] = root_i
                self.rank[root_i] += 1
            return True
        return False

def get_source_weight(source_type: str) -> float:
    """Return the precedence weight of a source type."""
    weights = {"csv": 0.90, "notes": 0.60}
    return weights.get(source_type.lower(), 0.0)

def match_candidates(records: List[RawCandidateRecord]) -> List[List[RawCandidateRecord]]:
    """Cluster raw candidate records using primary (email) and secondary (name/phone) matching rules."""
    n = len(records)
    uf = UnionFind(n)
    
    # Precompute normalized fields to avoid redundant calculations
    norm_emails = [normalize_email(r.email) if r.email else None for r in records]
    norm_phones = [normalize_phone(r.phone) if r.phone else None for r in records]
    norm_names = [normalize_name(r.full_name) if r.full_name else "" for r in records]

    # Primary match: share any normalized email
    email_to_idx = {}
    for i in range(n):
        email = norm_emails[i]
        if email:
            if email in email_to_idx:
                uf.union(i, email_to_idx[email])
            else:
                email_to_idx[email] = i

    # Secondary match: name similarity >= 85 AND shared phone (only if not already linked)
    try:
        from rapidfuzz import fuzz
    except ImportError:
        logger.error("rapidfuzz is not installed, secondary matching will be skipped.")
        fuzz = None

    if fuzz:
        for i in range(n):
            for j in range(i + 1, n):
                if uf.find(i) == uf.find(j):
                    continue
                
                # Verify both have a valid normalized phone that matches
                phone_i = norm_phones[i]
                phone_j = norm_phones[j]
                if phone_i and phone_j and phone_i == phone_j:
                    name_i = norm_names[i]
                    name_j = norm_names[j]
                    if name_i and name_j:
                        ratio = fuzz.token_sort_ratio(name_i, name_j)
                        if ratio >= 85:
                            uf.union(i, j)

    # Group records into clusters
    cluster_groups = defaultdict(list)
    for i in range(n):
        root = uf.find(i)
        cluster_groups[root].append(records[i])

    return list(cluster_groups.values())

def generate_candidate_id(cluster: List[RawCandidateRecord]) -> str:
    """Generate a deterministic UUID for a cluster of candidate records."""
    # Collect unique, normalized emails
    emails: Set[str] = set()
    for rec in cluster:
        if rec.email:
            norm_e = normalize_email(rec.email)
            if norm_e:
                emails.add(norm_e)

    if emails:
        # If emails exist: uuid5 using sorted emails
        seed_str = ",".join(sorted(list(emails)))
        return str(uuid.uuid5(uuid.NAMESPACE_URL, seed_str))

    # Sort cluster to find primary record deterministically
    sorted_cluster = sorted(
        cluster,
        key=lambda r: (-get_source_weight(r.source_type), r.source_path, r.raw_text or "")
    )
    primary_rec = sorted_cluster[0]
    
    seed_name = normalize_name(primary_rec.full_name) if primary_rec.full_name else ""
    seed_company = primary_rec.current_company.strip() if primary_rec.current_company else ""

    if seed_name or seed_company:
        # If no emails: uuid5 using normalized name + company
        seed_str = f"{seed_name}|{seed_company}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, seed_str))
    
    # If neither: uuid4 with warning
    logger.warning("No email, name, or company to seed deterministic UUID. Generating random UUID.")
    return str(uuid.uuid4())
