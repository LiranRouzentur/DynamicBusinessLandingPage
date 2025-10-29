"""Cache layer"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from landing_api.core.config import settings
import hashlib
import json


class CacheManager:
    """
    LRU cache by place_id with secondary hash validation.
    """
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_days = settings.cache_ttl_days
    
    def get(self, place_id: str, payload_hash: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get cached entry by place_id"""
        if place_id not in self.cache:
            return None
        
        entry = self.cache[place_id]
        
        # Check TTL
        if entry["expires_at"] < datetime.utcnow():
            del self.cache[place_id]
            return None
        
        # Validate secondary hash if provided
        if payload_hash and entry.get("payload_hash") != payload_hash:
            return None
        
        return entry["data"]
    
    def set(self, place_id: str, data: Dict[str, Any], payload_hash: Optional[str] = None):
        """Store entry in cache with TTL"""
        expires_at = datetime.utcnow() + timedelta(days=self.ttl_days)
        
        self.cache[place_id] = {
            "data": data,
            "payload_hash": payload_hash or self._hash_payload(data),
            "expires_at": expires_at,
            "created_at": datetime.utcnow(),
        }
    
    @staticmethod
    def _hash_payload(data: Dict[str, Any]) -> str:
        """Generate SHA256 hash of payload for validation"""
        payload_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()


# Global cache instance
cache_manager = CacheManager()


