import json
import logging
import sys
from typing import List
import click

from pipeline.loader import load_sources
from pipeline.extractors.csv_extractor import extract_csv
from pipeline.extractors.notes_extractor import extract_notes
from pipeline.matcher import match_candidates, generate_candidate_id
from pipeline.merger import merge_cluster
from pipeline.projector import project_profile
from pipeline.validator import validate_projected

def setup_logging(verbose: bool) -> None:
    """Configure stderr logging format and level based on verbosity."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        stream=sys.stderr,
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

@click.command()
@click.option('--csv', 'csv_paths', multiple=True, type=click.Path(exists=True), help='Path to recruiter CSV (can be repeated)')
@click.option('--notes', 'notes_paths', multiple=True, type=click.Path(exists=True), help='Path to recruiter notes .txt (can be repeated)')
@click.option('--config', 'config_path', type=click.Path(exists=True), help='Optional runtime config JSON')
@click.option('--output', 'output_path', type=click.Path(), help='Write result JSON (default: stdout, pretty-printed)')
@click.option('--verbose', is_flag=True, help='Enable DEBUG logging to stderr')
def main(csv_paths: List[str], notes_paths: List[str], config_path: str, output_path: str, verbose: bool) -> None:
    """ETL pipeline CLI entry point for the candidate-transformer tool."""
    setup_logging(verbose)
    
    # 1. Load files
    all_paths = list(csv_paths) + list(notes_paths)
    sources = load_sources(all_paths)
    
    # 2. Extract raw records
    raw_records = []
    for src in sources:
        if src.type == "csv":
            raw_records.extend(extract_csv(src))
        elif src.type == "notes":
            raw_records.extend(extract_notes(src))
            
    # 3. Match and cluster candidates
    clusters = match_candidates(raw_records)
    
    # Load configuration
    config_dict = None
    if config_path:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_dict = json.load(f)
        except Exception as e:
            click.echo(f"Failed to load config: {e}", err=True)
            sys.exit(1)
            
    # 4. Merge, project, and validate records
    results = []
    summary_candidates = []
    
    for cluster in clusters:
        candidate_id = generate_candidate_id(cluster)
        canonical_profile = merge_cluster(candidate_id, cluster)
        
        projected = project_profile(canonical_profile, config_dict)
        validated = validate_projected(projected, config_dict)
        
        results.append(validated)
        
        # Extract display values for logging execution summary
        name = validated.get("full_name") or canonical_profile.full_name or "Unknown Candidate"
        conf = validated.get("overall_confidence") or canonical_profile.overall_confidence
        summary_candidates.append((name, conf, candidate_id))
        
    # Serialize output (with sorted keys and pretty indentation)
    output_str = json.dumps(results, indent=2, sort_keys=True)
    
    if output_path:
        try:
            import os
            # Ensure output parent directories exist
            dir_name = os.path.dirname(output_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output_str)
            out_dest = output_path
        except Exception as e:
            click.echo(f"Failed to write output: {e}", err=True)
            sys.exit(1)
    else:
        click.echo(output_str)
        out_dest = "stdout"
        
    # Write summary block to stderr
    click.echo(f"[✓] Loaded {len(sources)} source file(s)", err=True)
    click.echo(f"[✓] Extracted {len(raw_records)} raw records", err=True)
    click.echo(f"[✓] Matched → {len(clusters)} candidate cluster(s)", err=True)
    click.echo(f"[✓] Output written to {out_dest}", err=True)
    
    for name, conf, cid in summary_candidates:
        click.echo(f"[✓] {name}  confidence: {conf:.2f}  id: {cid[:8]}...", err=True)

if __name__ == '__main__':
    main()
