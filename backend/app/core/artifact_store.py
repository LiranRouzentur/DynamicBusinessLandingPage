"""Artifact storage - Ref: Product.md > Section 9, lines 856-858"""

import os
from pathlib import Path
from typing import Optional, Dict
from app.core.config import settings


class ArtifactStore:
    """
    Stores generated bundles (index.html, styles.css, app.js).
    Path: /artifacts/{sessionId}/
    """
    
    def __init__(self):
        self.base_path = Path(settings.asset_store)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_bundle(
        self,
        session_id: str,
        index_html: str,
        styles_css: str,
        app_js: str
    ) -> str:
        """Save bundle to disk"""
        session_path = self.base_path / session_id
        session_path.mkdir(parents=True, exist_ok=True)
        
        # Write files
        (session_path / "index.html").write_text(index_html, encoding="utf-8")
        (session_path / "styles.css").write_text(styles_css, encoding="utf-8")
        (session_path / "app.js").write_text(app_js, encoding="utf-8")
        
        return str(session_path)
    
    def load_bundle(self, session_id: str) -> Optional[Dict[str, str]]:
        """Load bundle from disk"""
        session_path = self.base_path / session_id
        
        if not session_path.exists():
            return None
        
        return {
            "index_html": (session_path / "index.html").read_text(encoding="utf-8"),
            "styles_css": (session_path / "styles.css").read_text(encoding="utf-8"),
            "app_js": (session_path / "app.js").read_text(encoding="utf-8"),
        }
    
    def should_inline(self, bundle: Dict[str, str]) -> bool:
        """Check if bundle should be inlined"""
        total_size = sum(len(content.encode("utf-8")) for content in bundle.values())
        threshold_bytes = settings.inline_threshold_kb * 1024
        return total_size <= threshold_bytes


# Global store instance
artifact_store = ArtifactStore()


