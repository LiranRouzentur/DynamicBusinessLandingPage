"""Artifact storage"""

import os
import json
import base64
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from landing_api.core.config import settings

logger = logging.getLogger(__name__)


class ArtifactStore:
    """Stores only generated HTML in /artifacts/{sessionId}/index.html (optionally meta.json)."""
    def __init__(self):
        self.base_path = Path(settings.asset_store).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using path: {self.base_path}")

    def save_html(self, session_id: str, html: str, meta: Optional[dict] = None) -> str:
        """Save the single HTML output (and meta if provided)."""
        session_path = self.base_path / session_id
        session_path.mkdir(parents=True, exist_ok=True)
        (session_path / "index.html").write_text(html, encoding="utf-8")
        if meta is not None:
            (session_path / "meta.json").write_text(
                json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(session_path)

    def load_html(self, session_id: str) -> Optional[str]:
        """Load the HTML for this session."""
        session_path = self.base_path / session_id / "index.html"
        if not session_path.exists():
            return None
        return session_path.read_text(encoding="utf-8")

    def load_meta(self, session_id: str) -> Optional[dict]:
        """Optional: load the associated meta file."""
        meta_path = self.base_path / session_id / "meta.json"
        if not meta_path.exists():
            return None
        try:
            import json
            return json.load(meta_path.open("r", encoding="utf-8"))
        except Exception:
            return None


# Global store instance
artifact_store = ArtifactStore()


