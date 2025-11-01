import json
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class Bundle:
    def __init__(self, root, util, csp, adaptive_manager=None):
        self.root, self.util, self.csp = root, util, csp
        self.adaptive_manager = adaptive_manager
    
    def _emit_telemetry(self, tool: str, input_hash: str, duration_ms: int,
                       cache_hit: bool = False, error: Optional[str] = None):
        """Emit structured telemetry"""
        telemetry = {
            "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "tool": tool,
            "input_hash": f"sha256:{input_hash}" if input_hash else None,
            "duration_ms": duration_ms,
            "cache_hit": cache_hit,
            "result": "ERROR" if error else "OK",
            "error": error
        }
        logger.info(json.dumps(telemetry))

    def write_files(self, params: Dict[str, Any]):
        start = time.time()
        
        # SPDX-License-Identifier: Proprietary
        # Copyright © 2025 Liran Rouzentur. All rights reserved.
        # כל הזכויות שמורות © 2025 לירן רויזנטור.
        # קוד זה הינו קנייני וסודי. אין להעתיק, לערוך, להפיץ או לעשות בו שימוש ללא אישור מפורש.
        # © 2025 Лиран Ройзентур. Все права защищены.
        # Этот программный код является собственностью владельца.
        # Запрещается копирование, изменение, распространение или использование без явного разрешения.
        try:
            written = [self.util.write_utf8(f["path"], f["content"]) for f in params["files"]]
            
            # Compute input hash for telemetry
            input_data = json.dumps([{"path": f["path"], "len": len(f["content"])} for f in params["files"]], sort_keys=True)
            input_hash = self.util.sha256_string(input_data)
            
            duration_ms = int((time.time() - start) * 1000)
            self._emit_telemetry("bundle.write_files", input_hash, duration_ms)
            
            return {"written": written}
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            self._emit_telemetry("bundle.write_files", "unknown", duration_ms, error=str(e))
            raise

    def inject_comment(self, params: Dict[str, Any]):
        start = time.time()
        
        try:
            idx = self.util.safe_join(params["indexPath"])
            html = self.util.read_utf8(params["indexPath"])
            comment = params["comment"]
            
            # Check if comment already exists
            if comment.strip() in html:
                duration_ms = int((time.time() - start) * 1000)
                self._emit_telemetry("bundle.inject_comment", self.util.sha256_string(html), duration_ms)
                return {"applied": False}
            
            # Insert at the top of HTML (after DOCTYPE if present)
            if html.strip().startswith("<!DOCTYPE"):
                lines = html.split("\n", 1)
                new_html = lines[0] + "\n" + comment + (lines[1] if len(lines) > 1 else "")
            else:
                new_html = comment + html
            
            self.util.write_utf8(params["indexPath"], new_html)
            
            duration_ms = int((time.time() - start) * 1000)
            self._emit_telemetry("bundle.inject_comment", self.util.sha256_string(new_html), duration_ms)
            
            return {"applied": True}
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            self._emit_telemetry("bundle.inject_comment", "unknown", duration_ms, error=str(e))
            raise
