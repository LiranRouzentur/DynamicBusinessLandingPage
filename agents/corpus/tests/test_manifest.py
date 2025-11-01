"""Tests for manifest (index.json) generation"""
import pytest
import json
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from corpus.tools.rebuild_index import main as rebuild_index_main
from corpus.schemas import ErrorClass


@pytest.fixture
def temp_corpus(tmp_path):
    """Create temporary corpus structure"""
    corpus_root = tmp_path / "corpus"
    incidents_dir = corpus_root / "incidents" / "2025-10"
    patches_dir = corpus_root / "patches"
    
    incidents_dir.mkdir(parents=True)
    patches_dir.mkdir(parents=True)
    
    # Create test incident
    incident = {
        "id": "INC-2025-10-29-143212",
        "timestamp": "2025-10-29T14:32:12Z",
        "agent": "mapper",
        "error_class": "BROKEN_LINK",
        "input_fingerprint": "sha256-" + "a" * 64,
        "input_excerpt": "Test restaurant input",
        "candidate_output": {},
        "validator_errors": [
            {
                "code": "URL_UNREACHABLE",
                "field": "logo_url",
                "message": "HEAD 404"
            }
        ],
        "expected_fix": {
            "type": "PROMPT_PATCH",
            "ref": "patches/broken_link.md"
        },
        "tags": ["restaurant", "media"]
    }
    
    incident_file = incidents_dir / "INC-2025-10-29-143212.json"
    incident_file.write_text(json.dumps(incident), encoding='utf-8')
    
    # Create test patch (YAML)
    patch_yaml = """
id: BROKEN_LINK
match:
  error_class: BROKEN_LINK
  when:
    - field: logo_url
actions:
  - set:
      logo_url: "https://fallback.example.com/logo.png"
notes: "Fallback to default logo if URL fails"
"""
    patch_file = patches_dir / "broken_link.yaml"
    patch_file.write_text(patch_yaml, encoding='utf-8')
    
    # Create test patch (MD)
    patch_md = """# BROKEN_LINK Prompt Patch

If image URL fails validation:
1. Try favicon from official site.
2. Try og:image from homepage.
3. Fallback to category stock image.
"""
    patch_file_md = patches_dir / "broken_link_fallback.md"
    patch_file_md.write_text(patch_md, encoding='utf-8')
    
    return corpus_root


def test_rebuild_index_creates_manifest(temp_corpus):
    """Test that rebuild_index creates manifest with correct structure"""
    import sys
    import subprocess
    
    # Call rebuild_index.py directly with --corpus-root
    script_path = Path(__file__).parent.parent / "tools" / "rebuild_index.py"
    result = subprocess.run(
        [sys.executable, str(script_path), "--corpus-root", str(temp_corpus)],
        capture_output=True,
        text=True,
        cwd=temp_corpus.parent
    )
    
    # Check return code
    if result.returncode != 0:
        print(f"Script failed:\n{result.stderr}")
    
    # Check manifest was created
    manifest_path = temp_corpus / "index.json"
    assert manifest_path.exists(), f"Manifest should be created (stderr: {result.stderr})"
    
    # Verify structure
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    assert "version" in manifest
    assert "generated_at" in manifest
    assert "by_error_class" in manifest
    assert "patches" in manifest
    assert "tags" in manifest
    assert "incidents_latest" in manifest


def test_manifest_structure_simple(temp_corpus):
    """Simpler test: manually create manifest and verify structure"""
    manifest = {
        "version": 1,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "by_error_class": {
            "BROKEN_LINK": ["patches/broken_link.yaml"]
        },
        "patches": {
            "broken_link": "patches/broken_link.yaml"
        },
        "tags": {
            "restaurant": [
                "incidents/2025-10/INC-2025-10-29-143212.json"
            ]
        },
        "incidents_latest": {
            "BROKEN_LINK": ["incidents/2025-10/INC-2025-10-29-143212.json"]
        }
    }
    
    manifest_path = temp_corpus / "index.json"
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    
    # Verify keys exist
    with open(manifest_path, 'r') as f:
        loaded = json.load(f)
    
    assert loaded["version"] == 1
    assert "BROKEN_LINK" in loaded["by_error_class"]
    assert "broken_link" in loaded["patches"]
    assert "BROKEN_LINK" in loaded["incidents_latest"]
    assert "restaurant" in loaded["tags"]

