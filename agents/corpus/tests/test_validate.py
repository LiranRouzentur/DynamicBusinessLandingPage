"""Tests for validate.py"""
import pytest
import json
from pathlib import Path
import tempfile
import shutil

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from corpus.tools.validate import (
    validate_incident_schema,
    validate_patch_yaml,
    validate_patch_md,
    validate_manifest
)
from corpus.schemas import ErrorClass


def test_validate_incident_valid(tmp_path):
    """Test validation of valid incident"""
    incident = {
        "id": "INC-2025-10-29-143212",
        "timestamp": "2025-10-29T14:32:12Z",
        "agent": "mapper",
        "error_class": "BROKEN_LINK",
        "input_fingerprint": "sha256-" + "a" * 64,
        "input_excerpt": "Test input",
        "candidate_output": {},
        "validator_errors": [],
        "tags": []
    }
    
    incident_file = tmp_path / "test.json"
    incident_file.write_text(json.dumps(incident), encoding='utf-8')
    
    # Should not raise
    validate_incident_schema(incident_file)


def test_validate_incident_invalid_missing_field(tmp_path):
    """Test validation fails on missing required field"""
    incident = {
        "id": "INC-2025-10-29-143212",
        "timestamp": "2025-10-29T14:32:12Z",
        "agent": "mapper",
        # Missing error_class
        "input_fingerprint": "sha256-" + "a" * 64,
        "input_excerpt": "Test input"
    }
    
    incident_file = tmp_path / "test.json"
    incident_file.write_text(json.dumps(incident), encoding='utf-8')
    
    with pytest.raises(ValueError):
        validate_incident_schema(incident_file)


def test_validate_patch_yaml_valid(tmp_path):
    """Test validation of valid YAML patch"""
    patch_content = """
id: BROKEN_LINK
match:
  error_class: BROKEN_LINK
  when:
    - field: image_url
actions:
  - set:
      image_url: "https://fallback.example.com/image.jpg"
notes: "Fallback to default image if URL fails"
"""
    patch_file = tmp_path / "test.yaml"
    patch_file.write_text(patch_content, encoding='utf-8')
    
    # Should not raise
    validate_patch_yaml(patch_file)


def test_validate_patch_yaml_invalid_structure(tmp_path):
    """Test validation fails on invalid YAML structure"""
    patch_content = "not a mapping"
    patch_file = tmp_path / "test.yaml"
    patch_file.write_text(patch_content, encoding='utf-8')
    
    with pytest.raises(ValueError):
        validate_patch_yaml(patch_file)


def test_validate_patch_md_valid(tmp_path):
    """Test validation of valid Markdown patch"""
    patch_content = "# BROKEN_LINK Prompt Patch\n\nFix instructions here."
    patch_file = tmp_path / "test.md"
    patch_file.write_text(patch_content, encoding='utf-8')
    
    # Should not raise
    validate_patch_md(patch_file)


def test_validate_manifest_valid(tmp_path):
    """Test validation of valid manifest"""
    manifest = {
        "version": 1,
        "generated_at": "2025-10-29T14:40:00Z",
        "by_error_class": {
            "BROKEN_LINK": ["patches/broken_link.md"]
        },
        "patches": {
            "broken_link": "patches/broken_link.md"
        },
        "tags": {},
        "incidents_latest": {}
    }
    
    manifest_file = tmp_path / "index.json"
    manifest_file.write_text(json.dumps(manifest), encoding='utf-8')
    
    # Should not raise
    validate_manifest(manifest_file)


def test_validate_manifest_invalid_missing_key(tmp_path):
    """Test validation fails on missing required key"""
    manifest = {
        "version": 1
        # Missing generated_at
    }
    
    manifest_file = tmp_path / "index.json"
    manifest_file.write_text(json.dumps(manifest), encoding='utf-8')
    
    with pytest.raises(ValueError):
        validate_manifest(manifest_file)

