#!/usr/bin/env python3
"""Rebuild corpus index.json manifest"""
import json
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import tempfile
import shutil
import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from corpus.schemas import ErrorClass


def extract_error_class_from_patch(patch_file: Path) -> list:
    """Extract error classes that this patch matches"""
    error_classes = []
    
    if patch_file.suffix == '.yaml':
        try:
            with open(patch_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict) and 'match' in data:
                    match = data['match']
                    if isinstance(match, dict) and 'error_class' in match:
                        ec = match['error_class']
                        try:
                            ErrorClass(ec)  # Validate
                            error_classes.append(ec)
                        except ValueError:
                            pass
        except Exception:
            pass
    
    elif patch_file.suffix == '.md':
        # For MD patches, infer from filename patterns
        # e.g., broken_link.md -> BROKEN_LINK
        name_upper = patch_file.stem.upper().replace('-', '_')
        try:
            ErrorClass(name_upper)
            error_classes.append(name_upper)
        except ValueError:
            pass
    
    return error_classes


def extract_tags_from_patch(patch_file: Path) -> list:
    """Extract tags from patch file (filename or YAML metadata)"""
    tags = []
    
    # Infer from filename (split on underscores)
    name_parts = patch_file.stem.split('_')
    tags.extend([p.lower() for p in name_parts if len(p) > 2])
    
    if patch_file.suffix == '.yaml':
        try:
            with open(patch_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict) and 'tags' in data:
                    if isinstance(data['tags'], list):
                        tags.extend([str(t).lower() for t in data['tags']])
        except Exception:
            pass
    
    return list(set(tags))  # Deduplicate


def extract_tags_from_incident(incident_file: Path) -> list:
    """Extract tags from incident file"""
    try:
        with open(incident_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [str(t).lower() for t in data.get('tags', [])]
    except Exception:
        return []


def extract_error_class_from_incident(incident_file: Path) -> str:
    """Extract error class from incident file"""
    try:
        with open(incident_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('error_class', '')
    except Exception:
        return ''


def extract_timestamp_from_incident(incident_file: Path) -> str:
    """Extract timestamp from incident file"""
    try:
        with open(incident_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('timestamp', '')
    except Exception:
        return ''


def main():
    parser = argparse.ArgumentParser(description="Rebuild corpus index.json manifest")
    parser.add_argument('--corpus-root', type=Path, help="Override corpus root path")
    
    args = parser.parse_args()
    
    if args.corpus_root:
        corpus_root = args.corpus_root
    else:
        corpus_root = Path(__file__).resolve().parent.parent
    
    incidents_dir = corpus_root / "incidents"
    patches_dir = corpus_root / "patches"
    
    # Ensure directories exist
    incidents_dir.mkdir(parents=True, exist_ok=True)
    patches_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize manifest structure
    manifest = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "by_error_class": defaultdict(list),
        "patches": {},
        "incidents_latest": defaultdict(list),
        "tags": defaultdict(list)
    }
    
    # Scan patches
    print("Scanning patches...")
    for patch_file in sorted(patches_dir.glob("*.yaml")) + sorted(patches_dir.glob("*.md")):
        rel_path = str(patch_file.relative_to(corpus_root)).replace('\\', '/')  # Normalize paths
        patch_name = patch_file.stem
        
        manifest["patches"][patch_name] = rel_path
        
        # Map to error classes
        error_classes = extract_error_class_from_patch(patch_file)
        for ec in error_classes:
            manifest["by_error_class"][ec].append(rel_path)
        
        # Extract tags
        tags = extract_tags_from_patch(patch_file)
        for tag in tags:
            manifest["tags"][tag].append(rel_path)
    
    # Scan incidents
    print("Scanning incidents...")
    incident_files = []
    for incident_file in sorted(incidents_dir.rglob("INC-*.json")):
        incident_files.append(incident_file)
        rel_path = str(incident_file.relative_to(corpus_root)).replace('\\', '/')  # Normalize paths
        
        # Extract error class
        error_class = extract_error_class_from_incident(incident_file)
        if error_class:
            manifest["incidents_latest"][error_class].append(rel_path)
        
        # Extract tags
        tags = extract_tags_from_incident(incident_file)
        for tag in tags:
            manifest["tags"][tag].append(rel_path)
    
    # Sort incidents by timestamp (newest first) and limit to last 10 per error class
    for error_class in manifest["incidents_latest"]:
        incidents = manifest["incidents_latest"][error_class]
        # Get full paths to sort by timestamp
        incident_with_timestamps = []
        for rel_path in incidents:
            full_path = corpus_root / rel_path
            timestamp = extract_timestamp_from_incident(full_path)
            incident_with_timestamps.append((timestamp, rel_path))
        
        # Sort by timestamp descending
        incident_with_timestamps.sort(reverse=True, key=lambda x: x[0])
        # Keep last 10
        manifest["incidents_latest"][error_class] = [rel_path for _, rel_path in incident_with_timestamps[:10]]
    
    # Convert defaultdicts to regular dicts for JSON serialization
    manifest["by_error_class"] = dict(manifest["by_error_class"])
    manifest["incidents_latest"] = dict(manifest["incidents_latest"])
    manifest["tags"] = dict(manifest["tags"])
    
    # Write manifest (atomic)
    manifest_path = corpus_root / "index.json"
    
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=manifest_path.parent,
                                     delete=False, suffix='.tmp') as tmp:
        json.dump(manifest, tmp, indent=2, ensure_ascii=False)
        tmp_path = Path(tmp.name)
    
    try:
        shutil.move(str(tmp_path), str(manifest_path))
        rel_path = manifest_path.relative_to(corpus_root)
        print(f"\nManifest written: {rel_path}")
        print(f"  Patches: {len(manifest['patches'])}")
        print(f"  Incidents: {sum(len(v) for v in manifest['incidents_latest'].values())}")
        print(f"  Tags: {len(manifest['tags'])}")
        print(f"  Error classes: {len(manifest['by_error_class'])}")
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink()
        print(f"ERROR: Failed to write manifest: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

