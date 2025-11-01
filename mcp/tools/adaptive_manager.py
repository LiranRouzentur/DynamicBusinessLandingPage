"""Adaptive Manager for MCP - Policy hot-reload and tier shifting"""
import json
import pathlib
import time
import os
import logging
from typing import Dict, Any, List, Optional
from collections import deque
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class AdaptiveManager:
    """Manages policy hot-reload, tier shifting, and metrics collection"""
    
    def __init__(self, policies_dir: pathlib.Path):
        self.policies_dir = policies_dir
        self._last_reload = time.time()
        self._reload_interval = float(os.getenv("POLICY_RELOAD_INTERVAL_S", "5.0"))
        self._metrics_window = deque(maxlen=10)  # Last 10 builds
        
        # Load policies
        self.image_limits_path = policies_dir / "image_limits.json"
        self.domain_policies_path = policies_dir / "domain_policies.json"
        self.cache_policies_path = policies_dir / "cache_policies.json"
        
        self._image_limits = self._load_image_limits()
        self._domain_policies = self._load_domain_policies()
        self._cache_policies = self._load_cache_policies()
    
    def _load_image_limits(self) -> Dict[str, Any]:
        """Load image limits with tier support"""
        if not self.image_limits_path.exists():
            return {"tiers": {"default": {}}, "current_tier": "default"}
        return json.loads(self.image_limits_path.read_text(encoding="utf-8"))
    
    def _load_domain_policies(self) -> Dict[str, Any]:
        """Load domain-specific policies"""
        if not self.domain_policies_path.exists():
            return {"defaults": {}, "domains": {}}
        return json.loads(self.domain_policies_path.read_text(encoding="utf-8"))
    
    def _load_cache_policies(self) -> Dict[str, Any]:
        """Load cache policies"""
        if not self.cache_policies_path.exists():
            return {}
        return json.loads(self.cache_policies_path.read_text(encoding="utf-8"))
    
    def maybe_reload(self):
        """Check if policies need reloading"""
        now = time.time()
        if now - self._last_reload < self._reload_interval:
            return
        
        # Check mtimes
        reloaded = False
        if self.image_limits_path.exists():
            mtime = self.image_limits_path.stat().st_mtime
            if mtime > self._last_reload:
                self._image_limits = self._load_image_limits()
                reloaded = True
        
        if self.domain_policies_path.exists():
            mtime = self.domain_policies_path.stat().st_mtime
            if mtime > self._last_reload:
                self._domain_policies = self._load_domain_policies()
                reloaded = True
        
        if self.cache_policies_path.exists():
            mtime = self.cache_policies_path.stat().st_mtime
            if mtime > self._last_reload:
                self._cache_policies = self._load_cache_policies()
                reloaded = True
        
        if reloaded:
            self._last_reload = now
            logger.info(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "event": "policies_reloaded",
                "message": "Policy files reloaded"
            }))
    
    def get_limits(self, tier: Optional[str] = None) -> Dict[str, Any]:
        """Get image limits for current or specified tier"""
        self.maybe_reload()
        current_tier = tier or self._image_limits.get("current_tier", "default")
        tiers = self._image_limits.get("tiers", {})
        return tiers.get(current_tier, tiers.get("default", {}))
    
    def get_domain_policy(self, host: str) -> Dict[str, Any]:
        """Get policy for specific domain, with defaults fallback"""
        self.maybe_reload()
        defaults = self._domain_policies.get("defaults", {})
        domain_overrides = self._domain_policies.get("domains", {}).get(host, {})
        return {**defaults, **domain_overrides}
    
    def get_cache_policy(self) -> Dict[str, Any]:
        """Get cache policies"""
        self.maybe_reload()
        return self._cache_policies
    
    def record_build_metrics(self, metrics: Dict[str, Any]):
        """Record metrics from a build"""
        self._metrics_window.append({
            "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            **metrics
        })
        self._maybe_shift_tier()
    
    def _maybe_shift_tier(self):
        """Shift tier if metrics indicate need"""
        if len(self._metrics_window) < 10:
            return
        
        current_tier = self._image_limits.get("current_tier", "default")
        limits = self.get_limits(current_tier)
        max_mb = limits.get("total_images_max_mb", 1.5)
        
        # Check if recent builds exceed limits
        exceeded_count = 0
        high_latency_count = 0
        
        for metrics in list(self._metrics_window)[-10:]:
            total_mb = metrics.get("total_images_mb", 0)
            if total_mb > max_mb * 1.1:  # >10% over
                exceeded_count += 1
            
            p95_latency = metrics.get("p95_download_latency_ms", 0)
            if p95_latency > 5000:  # 5s threshold
                high_latency_count += 1
        
        # Shift to economy if >50% recent builds have issues
        if current_tier == "default" and (exceeded_count >= 5 or high_latency_count >= 5):
            self._image_limits["current_tier"] = "economy"
            logger.warning(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "event": "tier_shift",
                "from": "default",
                "to": "economy",
                "reason": f"exceeded={exceeded_count}, latency={high_latency_count}"
            }))
            # Write back (read-only in prod, but for dev)
            if self.image_limits_path.exists():
                try:
                    self.image_limits_path.write_text(json.dumps(self._image_limits, indent=2))
                except Exception:
                    pass
        
        # Shift back to default if metrics improve
        elif current_tier == "economy" and exceeded_count <= 2 and high_latency_count <= 2:
            self._image_limits["current_tier"] = "default"
            logger.info(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "event": "tier_shift",
                "from": "economy",
                "to": "default",
                "reason": "metrics_improved"
            }))
            if self.image_limits_path.exists():
                try:
                    self.image_limits_path.write_text(json.dumps(self._image_limits, indent=2))
                except Exception:
                    pass
    
    def get_allowed_domains(self) -> List[str]:
        """Get list of allowed domains"""
        self.maybe_reload()
        return self._image_limits.get("allowed_domains", [])
