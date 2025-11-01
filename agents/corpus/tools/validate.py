#!/usr/bin/env python3
"""Validate corpus files: incidents, patches, and manifest"""
import json
import argparse
import sys
from pathlib import Path
import yaml
from pydantic import ValidationError

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from corpus.schemas import Incident, ErrorClass


def validate_incident_schema(path: Path) -> None:
    """Validate incident file against schema. Raises on error."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        incident = Incident(**data)
        print(f"OK {path.name}: Valid incident schema")
    except json.JSONDecodeError as e:
        raise ValueError(f"{path.name}: Invalid JSON - {e}")
    except ValidationError as e:
        raise ValueError(f"{path.name}: Schema validation failed - {e}")
    except Exception as e:
        raise ValueError(f"{path.name}: Error - {e}")


def validate_patch_yaml(path: Path) -> None:
    """Validate YAML patch file structure. Raises on error."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not isinstance(data, dict):
            raise ValueError("YAML patch must be a mapping")
        
        # Basic structure check
        required_keys = ['id']
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key: {key}")
        
        # Check for match block if present
        if 'match' in data:
            match = data['match']
            if not isinstance(match, dict):
                raise ValueError("'match' must be a mapping")
            
            if 'error_class' in match:
                try:
                    ErrorClass(match['error_class'])
                except ValueError:
                    raise ValueError(f"Invalid error_class: {match['error_class']}")
        
        print(f"OK {path.name}: Valid YAML patch")
    except yaml.YAMLError as e:
        raise ValueError(f"{path.name}: Invalid YAML - {e}")
    except Exception as e:
        raise ValueError(f"{path.name}: Validation failed - {e}")


def validate_patch_md(path: Path) -> None:
    """Validate Markdown patch file. Basic check that it's readable."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            raise ValueError("Markdown patch file is empty")
        
        # Check for ID/header pattern
        if not (content.startswith('#') or 'BROKEN_LINK' in content[:100] or content.startswith('<!--')):
            print(f"WARN {path.name}: May not follow patch format (missing header)")
        
        print(f"OK {path.name}: Valid Markdown patch")
    except Exception as e:
        raise ValueError(f"{path.name}: Validation failed - {e}")


def validate_manifest(path: Path) -> None:
    """Validate manifest (index.json) structure. Raises on error."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            raise ValueError("Manifest must be a JSON object")
        
        required_keys = ['version', 'generated_at']
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key: {key}")
        
        # Check structure
        if 'by_error_class' not in data:
            raise ValueError("Missing 'by_error_class' key")
        
        if 'patches' not in data:
            raise ValueError("Missing 'patches' key")
        
        if 'tags' not in data:
            raise ValueError("Missing 'tags' key")
        
        # Validate error classes in by_error_class
        for error_class, paths in data.get('by_error_class', {}).items():
            try:
                ErrorClass(error_class)
            except ValueError:
                raise ValueError(f"Invalid error_class in manifest: {error_class}")
            
            if not isinstance(paths, list):
                raise ValueError(f"'by_error_class.{error_class}' must be a list")
        
        print(f"OK {path.name}: Valid manifest")
    except json.JSONDecodeError as e:
        raise ValueError(f"{path.name}: Invalid JSON - {e}")
    except Exception as e:
        raise ValueError(f"{path.name}: Validation failed - {e}")


def main():
    parser = argparse.ArgumentParser(description="Validate corpus files")
    parser.add_argument('--incident', type=Path, help="Path to incident file")
    parser.add_argument('--patch', type=Path, help="Path to patch file")
    parser.add_argument('--manifest', type=Path, help="Path to manifest (index.json)")
    parser.add_argument('--all', action='store_true', help="Validate all files in corpus")
    
    args = parser.parse_args()
    
    corpus_root = Path(__file__).resolve().parent.parent
    errors = []
    
    if args.all:
        # Validate all incidents
        incidents_dir = corpus_root / "incidents"
        for incident_file in incidents_dir.rglob("INC-*.json"):
            try:
                validate_incident_schema(incident_file)
            except ValueError as e:
                errors.append(str(e))
        
        # Validate all patches
        patches_dir = corpus_root / "patches"
        for patch_file in patches_dir.glob("*.yaml"):
            try:
                validate_patch_yaml(patch_file)
            except ValueError as e:
                errors.append(str(e))
        
        for patch_file in patches_dir.glob("*.md"):
            try:
                validate_patch_md(patch_file)
            except ValueError as e:
                errors.append(str(e))
        
        # Validate manifest
        manifest_path = corpus_root / "index.json"
        if manifest_path.exists():
            try:
                validate_manifest(manifest_path)
            except ValueError as e:
                errors.append(str(e))
        else:
            print("WARN index.json not found (run rebuild_index.py?)")
    
    else:
        if args.incident:
            try:
                validate_incident_schema(args.incident)
            except ValueError as e:
                errors.append(str(e))
        
        if args.patch:
            if args.patch.suffix == '.yaml':
                try:
                    validate_patch_yaml(args.patch)
                except ValueError as e:
                    errors.append(str(e))
            elif args.patch.suffix == '.md':
                try:
                    validate_patch_md(args.patch)
                except ValueError as e:
                    errors.append(str(e))
            else:
                errors.append(f"Unknown patch format: {args.patch.suffix}")
        
        if args.manifest:
            try:
                validate_manifest(args.manifest)
            except ValueError as e:
                errors.append(str(e))
    
    if errors:
        print("\nERROR: Validation errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
    else:
        print("\nOK All validations passed")


if __name__ == "__main__":
    main()

