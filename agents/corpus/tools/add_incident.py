#!/usr/bin/env python3
"""Add a new incident to the corpus"""
import json
import argparse
import sys
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from corpus.schemas import Incident, ErrorClass, ValidatorError, ExpectedFix


def compute_fingerprint(input_file: Path) -> str:
    """Compute SHA256 fingerprint of input file"""
    with open(input_file, 'rb') as f:
        content = f.read()
    hash_hex = hashlib.sha256(content).hexdigest()
    return f"sha256-{hash_hex}"


def read_input_excerpt(input_file: Path, max_chars: int = 500) -> str:
    """Read excerpt from input file"""
    try:
        if input_file.suffix == '.json':
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            excerpt = json.dumps(data, indent=2)[:max_chars]
        else:
            with open(input_file, 'r', encoding='utf-8') as f:
                excerpt = f.read(max_chars)
        
        if len(excerpt) == max_chars:
            excerpt += "..."
        return excerpt
    except Exception as e:
        return f"[Error reading input: {e}]"


def read_candidate_output(input_file: Path) -> dict:
    """Read candidate output if it's a JSON file"""
    if input_file.suffix == '.json':
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Try to find output in common keys
                if isinstance(data, dict):
                    return data.get("output", data.get("candidate_output", data))
        except:
            pass
    return {}


def main():
    parser = argparse.ArgumentParser(description="Add a new incident to corpus")
    parser.add_argument('--agent', required=True, help="Agent name (mapper|designer|orchestrator|<name>)")
    parser.add_argument('--error-class', required=True, type=str, help="Error class")
    parser.add_argument('--input-file', required=True, type=Path, help="Path to input file (JSON or text)")
    parser.add_argument('--validator-errors', type=Path, help="Path to validator errors JSON file")
    parser.add_argument('--expected-fix-ref', type=str, help="Reference to patch file")
    parser.add_argument('--expected-fix-type', choices=['JSON_PATCH', 'RULE_REF', 'PROMPT_PATCH'], 
                       default='PROMPT_PATCH', help="Expected fix type")
    parser.add_argument('--tags', type=str, help="Comma-separated tags")
    parser.add_argument('--candidate-output', type=Path, help="Path to candidate output file")
    
    args = parser.parse_args()
    
    corpus_root = Path(__file__).resolve().parent.parent
    
    # Validate error class
    try:
        error_class = ErrorClass(args.error_class)
    except ValueError:
        print(f"ERROR: Invalid error_class: {args.error_class}", file=sys.stderr)
        print(f"   Valid values: {', '.join([ec.value for ec in ErrorClass])}", file=sys.stderr)
        sys.exit(1)
    
    # Validate input file exists
    if not args.input_file.exists():
        print(f"ERROR: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    
    # Generate incident ID
    now = datetime.now(timezone.utc)
    timestamp_str = now.strftime("%Y-%m-%d-%H%M%S")
    incident_id = f"INC-{timestamp_str}"
    
    # Compute fingerprint
    input_fingerprint = compute_fingerprint(args.input_file)
    
    # Read input excerpt
    input_excerpt = read_input_excerpt(args.input_file)
    
    # Read candidate output
    candidate_output = {}
    if args.candidate_output:
        candidate_output = read_candidate_output(args.candidate_output)
    
    # Read validator errors
    validator_errors = []
    if args.validator_errors:
        if not args.validator_errors.exists():
            print(f"WARN: Validator errors file not found: {args.validator_errors}", file=sys.stderr)
        else:
            try:
                with open(args.validator_errors, 'r', encoding='utf-8') as f:
                    errors_data = json.load(f)
                if isinstance(errors_data, list):
                    validator_errors = [ValidatorError(**e) for e in errors_data]
                elif isinstance(errors_data, dict):
                    validator_errors = [ValidatorError(**errors_data)]
            except Exception as e:
                print(f"WARN: Error reading validator errors: {e}", file=sys.stderr)
    
    # Build expected fix
    expected_fix = None
    if args.expected_fix_ref:
        expected_fix = ExpectedFix(
            type=args.expected_fix_type,
            ref=args.expected_fix_ref
        )
    
    # Parse tags
    tags = []
    if args.tags:
        tags = [t.strip() for t in args.tags.split(',') if t.strip()]
    
    # Create incident
    incident = Incident(
        id=incident_id,
        timestamp=now.isoformat().replace('+00:00', 'Z'),
        agent=args.agent,
        error_class=error_class,
        input_fingerprint=input_fingerprint,
        input_excerpt=input_excerpt,
        candidate_output=candidate_output,
        validator_errors=validator_errors,
        expected_fix=expected_fix,
        tags=tags
    )
    
    # Write to file (atomic)
    incidents_dir = corpus_root / "incidents" / now.strftime("%Y-%m")
    incidents_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = incidents_dir / f"{incident_id}.json"
    
    # Atomic write: write to temp file then rename
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=output_file.parent, 
                                     delete=False, suffix='.tmp') as tmp:
        json.dump(incident.model_dump(), tmp, indent=2, ensure_ascii=False)
        tmp_path = Path(tmp.name)
    
    try:
        shutil.move(str(tmp_path), str(output_file))
        print(f"OK Incident written: {output_file.relative_to(corpus_root)}")
        print(f"  ID: {incident_id}")
        print(f"  Error class: {error_class.value}")
        print(f"  Tags: {', '.join(tags) if tags else 'none'}")
        print(f"\nNext step: Run 'python corpus/tools/rebuild_index.py' to update manifest")
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink()
        print(f"ERROR: Failed to write incident: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

