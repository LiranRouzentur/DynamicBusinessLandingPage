import requests, urllib.parse, json, pathlib, hashlib, time, sys
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from collections import defaultdict, deque

class CircuitBreaker:
    """Circuit breaker per domain"""
    def __init__(self, threshold: int = 5, cooldown_s: int = 60):
        self.threshold = threshold
        self.cooldown_s = cooldown_s
        self.failures = defaultdict(int)
        self.last_failure_time = {}
        self.circuit_open_until = {}
    
    def record_success(self, domain: str):
        """Reset failure count on success"""
        self.failures[domain] = 0
        if domain in self.circuit_open_until:
            del self.circuit_open_until[domain]
    
    def record_failure(self, domain: str):
        """Record failure and open circuit if threshold reached"""
        self.failures[domain] += 1
        self.last_failure_time[domain] = time.time()
        
        if self.failures[domain] >= self.threshold:
            self.circuit_open_until[domain] = time.time() + self.cooldown_s
            print(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "event": "circuit_open",
                "domain": domain,
                "failures": self.failures[domain]
            }), file=sys.stderr)
    
    def is_open(self, domain: str) -> bool:
        """Check if circuit is open"""
        if domain not in self.circuit_open_until:
            return False
        
        if time.time() >= self.circuit_open_until[domain]:
            # Circuit closed, reset
            del self.circuit_open_until[domain]
            self.failures[domain] = 0
            print(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "event": "circuit_closed",
                "domain": domain
            }), file=sys.stderr)
            return False
        
        return True

class RateLimiter:
    """Per-domain rate limiter"""
    def __init__(self, max_concurrency: int = 4):
        self.max_concurrency = defaultdict(lambda: max_concurrency)
        self.in_flight = defaultdict(int)
    
    def acquire(self, domain: str, max_concurrency: Optional[int] = None) -> bool:
        """Try to acquire slot"""
        limit = max_concurrency or self.max_concurrency[domain]
        if self.in_flight[domain] < limit:
            self.in_flight[domain] += 1
            return True
        return False
    
    def release(self, domain: str):
        """Release slot"""
        self.in_flight[domain] = max(0, self.in_flight[domain] - 1)

class HTTPCache:
    """HTTP cache with ETag/If-None-Match support"""
    def __init__(self, cache_root: pathlib.Path, ttl_s: int = 43200, max_mb: int = 512):
        self.cache_root = cache_root / "http"
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.ttl_s = ttl_s
        self.max_bytes = max_mb * 1024 * 1024
    
    def _cache_key(self, method: str, url: str, headers: Dict[str, str]) -> str:
        """Generate cache key"""
        canonical = f"{method}|{url}|{json.dumps(sorted(headers.items()), sort_keys=True)}"
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get from cache"""
        cache_file = self.cache_root / f"{key}.json"
        if not cache_file.exists():
            return None
        
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            age = time.time() - data.get("fetched_at", 0)
            if age > self.ttl_s:
                return None  # Expired
            return data
        except:
            return None
    
    def set(self, key: str, response_bytes: bytes, headers: Dict[str, Any], etag: Optional[str] = None):
        """Store in cache"""
        cache_file = self.cache_root / f"{key}.json"
        cache_file.write_text(json.dumps({
            "bytes": response_bytes.hex(),
            "headers": headers,
            "fetched_at": time.time(),
            "etag": etag
        }))
    
    def get_etag(self, headers: Dict[str, Any]) -> Optional[str]:
        """Extract ETag from response headers"""
        return headers.get("ETag") or headers.get("etag")

class Net:
    def __init__(self, allowlist: List[str], cache_root: Optional[pathlib.Path] = None, 
                 adaptive_manager=None, circuit_threshold: int = 5, cooldown_s: int = 60):
        self.allowlist = [d for d in allowlist if d]
        self.adaptive_manager = adaptive_manager
        self.circuit_breaker = CircuitBreaker(circuit_threshold, cooldown_s)
        self.rate_limiter = RateLimiter()
        self.cache = HTTPCache(cache_root or pathlib.Path("./mcp/storage/cache"), 
                               ttl_s=43200) if cache_root else None
    
    def _check_allowed(self, url: str):
        u = urllib.parse.urlparse(url)
        if u.scheme != "https": 
            raise ValueError("only https is allowed")
        
        # Check adaptive manager allowed domains if available
        if self.adaptive_manager:
            allowed = self.adaptive_manager.get_allowed_domains()
            if allowed and not any(u.netloc.endswith(d) for d in allowed):
                raise ValueError(f"domain not allowlisted: {u.netloc}")
        elif self.allowlist and not any(u.netloc.endswith(d) for d in self.allowlist):
            raise ValueError(f"domain not allowlisted: {u.netloc}")
    
    def _emit_telemetry(self, tool: str, domain: str, duration_ms: int, 
                       cache_hit: bool = False, revalidated: bool = False,
                       error: Optional[str] = None):
        """Emit structured telemetry"""
        telemetry = {
            "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "tool": tool,
            "domain": domain,
            "duration_ms": duration_ms,
            "cache": {"hit": cache_hit, "revalidated": revalidated},
            "result": "ERROR" if error else "OK",
            "error": error
        }
        print(json.dumps(telemetry), file=sys.stderr)
    
    def head(self, params: Dict[str, Any]):
        """HEAD request with caching and circuit breaking"""
        url = params["url"]
        timeout = float(params.get("timeoutMs", 3500))/1000.0
        
        self._check_allowed(url)
        domain = urllib.parse.urlparse(url).netloc
        
        # Check circuit breaker
        if self.circuit_breaker.is_open(domain):
            raise ValueError(f"Circuit breaker open for {domain}")
        
        start = time.time()
        cache_hit = False
        revalidated = False
        
        try:
            # Try cache if available
            if self.cache:
                cache_key = self.cache._cache_key("HEAD", url, {})
                cached = self.cache.get(cache_key)
                if cached:
                    cache_hit = True
                    duration_ms = int((time.time() - start) * 1000)
                    self._emit_telemetry("net.head", domain, duration_ms, cache_hit=True)
                    self.circuit_breaker.record_success(domain)
                    return {"status": cached["headers"].get("status", 200), 
                           "headers": cached["headers"], "cache_hit": True}
            
            # Make request
            headers = {}
            if self.cache:
                cache_key = self.cache._cache_key("HEAD", url, {})
                cached = self.cache.get(cache_key)
                if cached and cached.get("etag"):
                    headers["If-None-Match"] = cached["etag"]
            
            r = requests.head(url, timeout=timeout, allow_redirects=True, headers=headers)
            
            # Handle 304 Not Modified
            if r.status_code == 304 and cached:
                revalidated = True
                duration_ms = int((time.time() - start) * 1000)
                self._emit_telemetry("net.head", domain, duration_ms, cache_hit=True, revalidated=True)
                self.circuit_breaker.record_success(domain)
                return {"status": 200, "headers": cached["headers"], "cache_hit": True, "revalidated": True}
            
            duration_ms = int((time.time() - start) * 1000)
            result = {"status": r.status_code, "headers": dict(r.headers), 
                     "cache_hit": False, "revalidated": False}
            
            # Cache response
            if self.cache and r.status_code == 200:
                etag = self.cache.get_etag(r.headers)
                # For HEAD, we don't cache body, just metadata
                pass
            
            self._emit_telemetry("net.head", domain, duration_ms, cache_hit=False)
            self.circuit_breaker.record_success(domain)
            return result
            
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            self._emit_telemetry("net.head", domain, duration_ms, error=str(e))
            self.circuit_breaker.record_failure(domain)
            raise
    
    def get_bytes(self, url: str, timeout: Optional[float] = None, 
                  retries: int = 2) -> bytes:
        """GET with caching, rate limiting, circuit breaking, retries"""
        self._check_allowed(url)
        domain = urllib.parse.urlparse(url).netloc
        
        # Get domain policy
        if self.adaptive_manager:
            policy = self.adaptive_manager.get_domain_policy(domain)
            timeout = timeout or (policy.get("timeout_ms", 3500) / 1000.0)
            retries = retries or policy.get("retries", 2)
            max_concurrency = policy.get("concurrency", 4)
        else:
            timeout = timeout or 5.0
        
        # Check circuit breaker
        if self.circuit_breaker.is_open(domain):
            raise ValueError(f"Circuit breaker open for {domain}")
        
        # Rate limiting
        if not self.rate_limiter.acquire(domain, max_concurrency if self.adaptive_manager else None):
            raise ValueError(f"Rate limit exceeded for {domain}")
        
        start = time.time()
        cache_hit = False
        revalidated = False
        
        try:
            # Try cache
            if self.cache:
                cache_key = self.cache._cache_key("GET", url, {})
                cached = self.cache.get(cache_key)
                if cached:
                    cache_hit = True
                    duration_ms = int((time.time() - start) * 1000)
                    self._emit_telemetry("net.get_bytes", domain, duration_ms, cache_hit=True)
                    self.circuit_breaker.record_success(domain)
                    self.rate_limiter.release(domain)
                    return bytes.fromhex(cached["bytes"])
            
            # Make request with retries
            last_error = None
            for attempt in range(retries + 1):
                try:
                    headers = {}
                    if self.cache and attempt == 0:
                        cache_key = self.cache._cache_key("GET", url, {})
                        cached = self.cache.get(cache_key)
                        if cached and cached.get("etag"):
                            headers["If-None-Match"] = cached["etag"]
                    
                    r = requests.get(url, timeout=timeout, stream=True, headers=headers)
                    
                    # Handle 304 Not Modified
                    if r.status_code == 304 and cached:
                        revalidated = True
                        duration_ms = int((time.time() - start) * 1000)
                        self._emit_telemetry("net.get_bytes", domain, duration_ms, cache_hit=True, revalidated=True)
                        self.circuit_breaker.record_success(domain)
                        self.rate_limiter.release(domain)
                        return bytes.fromhex(cached["bytes"])
                    
                    r.raise_for_status()
                    data = r.content
                    
                    # Cache response
                    if self.cache and r.status_code == 200:
                        etag = self.cache.get_etag(r.headers)
                        self.cache.set(cache_key, data, dict(r.headers), etag)
                    
                    duration_ms = int((time.time() - start) * 1000)
                    self._emit_telemetry("net.get_bytes", domain, duration_ms, cache_hit=False)
                    self.circuit_breaker.record_success(domain)
                    self.rate_limiter.release(domain)
                    return data
                    
                except Exception as e:
                    last_error = e
                    if attempt < retries:
                        time.sleep(min(2 ** attempt, 5))
                        continue
                    raise
            
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            self._emit_telemetry("net.get_bytes", domain, duration_ms, error=str(e))
            self.circuit_breaker.record_failure(domain)
            self.rate_limiter.release(domain)
            raise last_error if last_error else e
