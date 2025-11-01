#!/usr/bin/env python3
"""Retrieve patches and incidents from corpus"""
import json
import argparse
import sys
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from corpus.schemas import ErrorClass


def load_manifest(corpus_root: Path) -> dict:
    """Load manifest, raising on error"""
    manifest_path = corpus_root / "index.json"
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found: {manifest_path}", file=sys.stderr)
        print("   Run: python corpus/tools/rebuild_index.py", file=sys.stderr)
        sys.exit(1)
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def retrieve_exact(error_class: str, manifest: dict, corpus_root: Path) -> List[str]:
    """Retrieve patch file paths for error class"""
    patches = manifest.get("by_error_class", {}).get(error_class, [])
    return [str(corpus_root / p) for p in patches]


def retrieve_incidents(error_class: str, limit: int, manifest: dict, corpus_root: Path) -> List[str]:
    """Retrieve latest incident file paths for error class"""
    incidents = manifest.get("incidents_latest", {}).get(error_class, [])[:limit]
    return [str(corpus_root / p) for p in incidents]


def retrieve_tags(tag: str, manifest: dict, corpus_root: Path) -> List[str]:
    """Retrieve file paths for tag"""
    files = manifest.get("tags", {}).get(tag.lower(), [])
    return [str(corpus_root / p) for p in files]


def text_search(pattern: str, corpus_root: Path) -> List[str]:
    """Text search using ripgrep if available, else Python grep"""
    import subprocess
    
    # Try ripgrep first
    try:
        result = subprocess.run(
            ['rg', '-l', pattern, str(corpus_root)],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Fallback to Python grep
    matches = []
    for file_path in corpus_root.rglob("*"):
        if file_path.is_file() and file_path.suffix in ['.json', '.md', '.yaml']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if pattern in content:
                        matches.append(str(file_path))
            except Exception:
                pass
    
    return matches


def main():
    parser = argparse.ArgumentParser(description="Retrieve patches and incidents from corpus")
    subparsers = parser.add_subparsers(dest='command', help='Subcommand')
    
    # exact command
    exact_parser = subparsers.add_parser('exact', help='Retrieve patches by error class')
    exact_parser.add_argument('--error-class', required=True, type=str, help="Error class")
    
    # incidents command
    incidents_parser = subparsers.add_parser('incidents', help='Retrieve incidents by error class')
    incidents_parser.add_argument('--error-class', required=True, type=str, help="Error class")
    incidents_parser.add_argument('--limit', type=int, default=5, help="Limit number of incidents")
    
    # tags command
    tags_parser = subparsers.add_parser('tags', help='Retrieve files by tag')
    tags_parser.add_argument('--tag', required=True, type=str, help="Tag name")
    
    # text command
    text_parser = subparsers.add_parser('text', help='Text search across corpus')
    text_parser.add_argument('--pattern', required=True, type=str, help="Search pattern")
    
    args = parser.parse_args()
    
    corpus_root = Path(__file__).resolve().parent.parent
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'exact':
        try:
            ErrorClass(args.error_class)  # Validate
        except ValueError:
            print(f"❌ Invalid error_class: {args.error_class}", file=sys.stderr)
            sys.exit(1)
        
        manifest = load_manifest(corpus_root)
        patches = retrieve_exact(args.error_class, manifest, corpus_root)
        
        if patches:
            for patch in patches:
                print(patch)
        else:
            print(f"No patches found for error_class: {args.error_class}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == 'incidents':
        try:
            ErrorClass(args.error_class)  # Validate
        except ValueError:
            print(f"❌ Invalid error_class: {args.error_class}", file=sys.stderr)
            sys.exit(1)
        
        manifest = load_manifest(corpus_root)
        incidents = retrieve_incidents(args.error_class, args.limit, manifest, corpus_root)
        
        if incidents:
            for incident in incidents:
                print(incident)
        else:
            print(f"No incidents found for error_class: {args.error_class}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == 'tags':
        manifest = load_manifest(corpus_root)
        files = retrieve_tags(args.tag, manifest, corpus_root)
        
        if files:
            for file_path in files:
                print(file_path)
        else:
            print(f"No files found for tag: {args.tag}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == 'text':
        matches = text_search(args.pattern, corpus_root)
        
        if matches:
            for match in matches:
                print(match)
        else:
            print(f"No matches found for pattern: {args.pattern}", file=sys.stderr)
            sys.exit(1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

