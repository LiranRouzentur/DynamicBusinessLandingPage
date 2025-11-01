"""Corpus client for agent integration - loads patches and incidents"""
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Cache for manifest with mtime check
_manifest_cache = None
_manifest_mtime = None


def _get_corpus_root() -> Path:
    """Get corpus root directory"""
    # Try to find corpus relative to this file
    current_file = Path(__file__).resolve()
    corpus_root = current_file.parent.parent / "corpus"
    
    # Allow override via environment variable
    env_root = os.getenv("CORPUS_ROOT")
    if env_root:
        corpus_root = Path(env_root)
    
    return corpus_root


def load_manifest(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load manifest with caching and mtime check.
    
    Args:
        force_reload: Force reload even if cached
    
    Returns:
        Manifest dictionary
    """
    global _manifest_cache, _manifest_mtime
    
    corpus_root = _get_corpus_root()
    manifest_path = corpus_root / "index.json"
    
    if not manifest_path.exists():
        logger.warning(f"Corpus manifest not found: {manifest_path}")
        return {
            "version": 1,
            "by_error_class": {},
            "patches": {},
            "incidents_latest": {},
            "tags": {}
        }
    
    # Check mtime for cache invalidation
    current_mtime = manifest_path.stat().st_mtime
    
    if not force_reload and _manifest_cache is not None and _manifest_mtime == current_mtime:
        return _manifest_cache
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            _manifest_cache = json.load(f)
            _manifest_mtime = current_mtime
            return _manifest_cache
    except Exception as e:
        logger.error(f"Failed to load corpus manifest: {e}")
        return {
            "version": 1,
            "by_error_class": {},
            "patches": {},
            "incidents_latest": {},
            "tags": {}
        }


def patches_for_error(error_class: str) -> List[str]:
    """
    Get patch file paths for a given error class.
    
    Args:
        error_class: Error class enum value
    
    Returns:
        List of patch file paths (as strings)
    """
    manifest = load_manifest()
    patches = manifest.get("by_error_class", {}).get(error_class, [])
    corpus_root = _get_corpus_root()
    return [str(corpus_root / p) for p in patches]


def fewshots_for_error(error_class: str, limit: int = 2) -> List[str]:
    """
    Load patch file contents for error class as few-shot examples.
    
    Args:
        error_class: Error class enum value
        limit: Maximum number of patches to return
    
    Returns:
        List of patch file contents (as strings)
    """
    patch_paths = patches_for_error(error_class)[:limit]
    contents = []
    
    for patch_path in patch_paths:
        try:
            with open(patch_path, 'r', encoding='utf-8') as f:
                contents.append(f.read())
        except Exception as e:
            logger.warning(f"Failed to read patch {patch_path}: {e}")
    
    return contents


def incident_examples(error_class: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Load latest incidents for error class, returning subset of fields.
    
    Args:
        error_class: Error class enum value
        limit: Maximum number of incidents to return
    
    Returns:
        List of incident dictionaries with fields: input_excerpt, expected_fix, validator_errors
    """
    manifest = load_manifest()
    incidents = manifest.get("incidents_latest", {}).get(error_class, [])[:limit]
    corpus_root = _get_corpus_root()
    
    examples = []
    for rel_path in incidents:
        incident_path = corpus_root / rel_path
        try:
            with open(incident_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                examples.append({
                    "input_excerpt": data.get("input_excerpt", ""),
                    "expected_fix": data.get("expected_fix"),
                    "validator_errors": data.get("validator_errors", []),
                    "id": data.get("id", "")
                })
        except Exception as e:
            logger.warning(f"Failed to read incident {incident_path}: {e}")
    
    return examples


def format_fewshot_prompt(error_class: str, limit_patches: int = 2, limit_incidents: int = 2) -> str:
    """
    Format a prompt patch section with few-shot examples.
    
    Args:
        error_class: Error class enum value
        limit_patches: Max patches to include
        limit_incidents: Max incidents to include
    
    Returns:
        Formatted string to prepend to agent prompts
    """
    patches = fewshots_for_error(error_class, limit_patches)
    incidents = incident_examples(error_class, limit_incidents)
    
    if not patches and not incidents:
        return ""  # No corpus data available
    
    lines = [
        "## Prompt Patches & Examples (from incident corpus)",
        ""
    ]
    
    if patches:
        lines.append("### Relevant Patches:")
        for i, patch_content in enumerate(patches, 1):
            lines.append(f"#### Patch {i}:")
            lines.append(patch_content)
            lines.append("")
    
    if incidents:
        lines.append("### Recent Incident Examples:")
        for incident in incidents:
            lines.append(f"**Incident {incident.get('id', 'unknown')}:**")
            if incident.get("expected_fix"):
                fix = incident["expected_fix"]
                if fix.get("ref"):
                    lines.append(f"Fix reference: {fix['ref']}")
                if fix.get("notes"):
                    lines.append(f"Notes: {fix['notes']}")
            if incident.get("validator_errors"):
                lines.append("Validator errors:")
                for err in incident["validator_errors"][:2]:  # Limit to first 2
                    lines.append(f"  - {err.get('code', 'unknown')}: {err.get('message', '')}")
            lines.append("")
    
    return "\n".join(lines)

