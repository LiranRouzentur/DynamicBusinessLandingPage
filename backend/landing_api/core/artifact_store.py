"""Artifact storage"""

import os
import base64
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from landing_api.core.config import settings

logger = logging.getLogger(__name__)


class ArtifactStore:
    """
    Stores generated bundles (index.html, styles.css, app.js).
    Path: /artifacts/{sessionId}/
    """
    
    def __init__(self):
        # Use absolute path to ensure consistency regardless of working directory
        self.base_path = Path(settings.asset_store).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using path: {self.base_path}")
    
    def save_bundle(
        self,
        session_id: str,
        index_html: str,
        styles_css: str,
        app_js: str,
        assets: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save bundle to disk"""
        session_path = self.base_path / session_id
        session_path.mkdir(parents=True, exist_ok=True)
        
        # Write main files
        (session_path / "index.html").write_text(index_html, encoding="utf-8")
        (session_path / "styles.css").write_text(styles_css, encoding="utf-8")
        (session_path / "app.js").write_text(app_js, encoding="utf-8")
        
        # Save assets if provided
        if assets and assets.get("images"):
            assets_dir = session_path / "assets" / "images"
            assets_dir.mkdir(parents=True, exist_ok=True)
            
            for img in assets["images"]:
                filename = img.get("filename", "image.webp")
                base64_data = img.get("base64", "")
                if base64_data:
                    try:
                        binary_data = base64.b64decode(base64_data)
                        
                        # Write image file
                        target_path = assets_dir / filename
                        target_path.write_bytes(binary_data)
                        logger.debug(f"Saved image: {target_path}")
                    except Exception as e:
                        logger.error(f"Error saving image {filename}: {e}")
        
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


