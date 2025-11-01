#!/usr/bin/env python3
"""Add or update a patch file"""
import argparse
import sys
from pathlib import Path
import tempfile
import shutil
import yaml

def create_md_template(name: str) -> str:
    """Create Markdown patch template"""
    return f"""# {name.upper().replace('_', ' ')} Prompt Patch

## Context
Describe when this patch applies.

## Fix Instructions
1. Step 1
2. Step 2
3. Step 3

## Example
Show a concrete example of the fix.

## References
- Related incidents: INC-...
- Related patches: ...
"""


def create_yaml_template(name: str, error_class: str = None) -> str:
    """Create YAML patch template"""
    template = {
        'id': name.upper().replace('-', '_'),
        'match': {
            'error_class': error_class or 'MISSING_REQUIRED',
            'when': [
                {'field': 'example_field'}
            ]
        },
        'actions': [
            {
                'set': {
                    'example_field': 'default_value'
                }
            }
        ],
        'retry': {
            'attempts': 1
        },
        'notes': 'Description of when and how to apply this patch'
    }
    return yaml.dump(template, default_flow_style=False, sort_keys=False)


def main():
    parser = argparse.ArgumentParser(description="Add or update a patch file")
    parser.add_argument('--name', required=True, help="Patch name (without extension)")
    parser.add_argument('--type', choices=['md', 'yaml'], required=True, help="Patch type")
    parser.add_argument('--from', dest='from_file', type=Path, help="Copy from existing file")
    parser.add_argument('--editor', action='store_true', help="Open in $EDITOR (not implemented)")
    parser.add_argument('--error-class', type=str, help="Error class for YAML template")
    
    args = parser.parse_args()
    
    corpus_root = Path(__file__).resolve().parent.parent
    patches_dir = corpus_root / "patches"
    patches_dir.mkdir(parents=True, exist_ok=True)
    
    ext = args.type
    output_file = patches_dir / f"{args.name}.{ext}"
    
    if args.from_file:
        # Copy from existing file
        if not args.from_file.exists():
            print(f"ERROR: Source file not found: {args.from_file}", file=sys.stderr)
            sys.exit(1)
        
        # Atomic write
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=output_file.parent,
                                         delete=False, suffix='.tmp') as tmp:
            with open(args.from_file, 'r', encoding='utf-8') as src:
                tmp.write(src.read())
            tmp_path = Path(tmp.name)
        
        try:
            shutil.move(str(tmp_path), str(output_file))
            print(f"OK Patch copied: {output_file.relative_to(corpus_root)}")
        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink()
            print(f"ERROR: Failed to write patch: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.editor:
        print("WARN: Editor mode not implemented. Use --from to copy a template file.")
        sys.exit(1)
    
    else:
        # Create new file from template
        if output_file.exists():
            response = input(f"WARN: {output_file.name} already exists. Overwrite? [y/N]: ")
            if response.lower() != 'y':
                print("Cancelled.")
                sys.exit(0)
        
        if ext == 'md':
            content = create_md_template(args.name)
        else:  # yaml
            content = create_yaml_template(args.name, args.error_class)
        
        # Atomic write
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=output_file.parent,
                                         delete=False, suffix='.tmp') as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        
        try:
            shutil.move(str(tmp_path), str(output_file))
            print(f"OK Patch created: {output_file.relative_to(corpus_root)}")
            print(f"  Edit the file to customize the patch")
        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink()
            print(f"ERROR: Failed to write patch: {e}", file=sys.stderr)
            sys.exit(1)
    
    print(f"\nNext step: Run 'python corpus/tools/rebuild_index.py' to update manifest")


if __name__ == "__main__":
    main()

