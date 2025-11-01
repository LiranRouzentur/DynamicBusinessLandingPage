import hashlib, json, pathlib, time
from typing import Any, Dict, Optional
from datetime import datetime, timezone

class Util:
    def __init__(self, root): 
        self.root = pathlib.Path(root)
        self._config_cache = {}
        self._config_mtimes = {}
    
    def safe_join(self, relpath: str) -> pathlib.Path:
        # Resolve both root and path to absolute paths for comparison
        root_resolved = self.root.resolve()
        p = (root_resolved / relpath).resolve()
        # Check if resolved path is within resolved root
        try:
            # Check if root is in path's parents or is the path itself
            if root_resolved != p and not p.is_relative_to(root_resolved):
                raise ValueError(f"path escapes workspace: {relpath} (resolved to {p}, root is {root_resolved})")
        except AttributeError:
            # Python < 3.9 fallback: check if root is in path's parents
            if root_resolved != p:
                # Check if any parent of p equals root_resolved
                for parent in p.parents:
                    if parent == root_resolved:
                        break
                else:
                    # root_resolved not found in p.parents
                    raise ValueError(f"path escapes workspace: {relpath} (resolved to {p}, root is {root_resolved})")
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    
    def sha256_bytes(self, b: bytes) -> str:
        return hashlib.sha256(b).hexdigest()
    
    def sha256_string(self, s: str) -> str:
        return hashlib.sha256(s.encode("utf-8")).hexdigest()
    
    def write_utf8(self, path: str, content: str):
        p = self.safe_join(path)
        data = content.encode("utf-8")
        p.write_bytes(data)
        return {"path": str(p.relative_to(self.root)), "bytes": len(data), "sha256": self.sha256_bytes(data)}
    
    def read_utf8(self, path: str) -> str:
        """Read text file from workspace"""
        p = self.safe_join(path)
        return p.read_text(encoding="utf-8")
    
    def load_json(self, path: str, reload: bool = False) -> Dict[str, Any]:
        """Load JSON with optional hot-reload detection"""
        path_obj = pathlib.Path(path)
        current_mtime = path_obj.stat().st_mtime if path_obj.exists() else 0
        
        if not reload and path in self._config_cache:
            cached_mtime = self._config_mtimes.get(path, 0)
            if current_mtime <= cached_mtime:
                return self._config_cache[path]
        
        data = json.loads(path_obj.read_text(encoding="utf-8"))
        self._config_cache[path] = data
        self._config_mtimes[path] = current_mtime
        return data
    
    def read_text(self, path: str) -> str:
        return pathlib.Path(path).read_text(encoding="utf-8")
    
    def hash_dir(self, _params=None):
        """Compute deterministic tree hash of workspace"""
        out = []
        for fp in sorted(self.root.rglob("*")):
            if fp.is_file():
                rel = fp.relative_to(self.root)
                out.append({"path": str(rel), "sha256": self.sha256_bytes(fp.read_bytes())})
        out.sort(key=lambda x: x["path"])
        # Hash the sorted list for deterministic tree hash
        tree_repr = json.dumps(out, sort_keys=True)
        tree_hash = self.sha256_string(tree_repr)
        return {"files": out, "tree_hash": tree_hash}
    
    def timestamp(self) -> str:
        """ISO timestamp for telemetry"""
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
