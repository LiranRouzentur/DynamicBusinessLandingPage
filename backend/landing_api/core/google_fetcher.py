"""Google Places API v1 client - HTTP-based implementation"""

from typing import Optional, List, Dict, Any
import httpx
import logging
import asyncio
from landing_api.core.config import settings
from landing_api.models.errors import ApplicationError, ErrorCode

logger = logging.getLogger(__name__)

PLACES_BASE = "https://places.googleapis.com/v1"
MAX_PHOTOS = 4  # How many photo URIs to resolve
PHOTO_MAX_WIDTH = 1600  # Max width for photo resolution


class GoogleFetcher:
    """
    Fetches Place Details, Photos, Reviews from Google Places API v1.
    
    Uses HTTP-based Places API v1 for direct calls:
    - Place Details endpoint
    - Photo Media endpoint for URI resolution
    
    Returns data in the format expected by the orchestrator.
    """
    
    # Initializes Google Places API client with API key from settings; warns if key missing.
    # Creates persistent async HTTP client for efficient API calls with 20s timeout.
    def __init__(self):
        if not settings.google_maps_api_key:
            logger.warning("GOOGLE_MAPS_API_KEY not set in .env file")
        self.api_key = settings.google_maps_api_key
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=20.0)
        return self._client
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _get(
        self, 
        url: str, 
        headers: Dict[str, str], 
        params: Optional[Dict[str, Any]] = None,
        retries: int = 3
    ) -> httpx.Response:
        """HTTP GET with retry logic for 429/5xx errors"""
        client = await self._get_client()
        for i in range(retries):
            try:
                response = await client.get(url, headers=headers, params=params or {})
                if response.status_code in (429, 500, 503) and i < retries - 1:
                    await asyncio.sleep(0.7 * (i + 1))
                    continue
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if i == retries - 1:
                    raise
                await asyncio.sleep(0.7 * (i + 1))
        raise httpx.HTTPError("Max retries exceeded")
    
    async def _fetch_place_details(self, place_id: str) -> Dict[str, Any]:
        """Fetch place details from Google Places API v1"""
        field_mask = ",".join([
            # identity + links
            "id", "name", "displayName", "types", "primaryType", "googleMapsUri", "websiteUri",
            # location
            "formattedAddress", "addressComponents", "location", "viewport",
            # contact
            "internationalPhoneNumber",
            # hours/status
            "currentOpeningHours", "currentOpeningHours.openNow",
            "regularOpeningHours", "regularOpeningHours.weekdayDescriptions",
            # ratings
            "rating", "userRatingCount", "priceLevel",
            # editorial
            "editorialSummary",
            # photos (metadata only; URIs come from photo media endpoint)
            "photos.name", "photos.widthPx", "photos.heightPx", "photos.authorAttributions",
            # reviews (limited to 5 by API)
            "reviews.rating", "reviews.text", "reviews.publishTime",
            "reviews.authorAttribution", "reviews.relativePublishTimeDescription"
        ])
        
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask,
        }
        
        url = f"{PLACES_BASE}/places/{place_id}"
        response = await self._get(url, headers=headers)
        return response.json()
    
    async def _resolve_photo_uri(self, photo_name: str, max_width: int) -> Optional[str]:
        """Resolve photo URI using photo media endpoint"""
        headers = {"X-Goog-Api-Key": self.api_key}
        # Ask for JSON so we don't follow the 302; gives short-lived photoUri
        params = {"maxWidthPx": max_width, "skipHttpRedirect": "true"}
        url = f"{PLACES_BASE}/{photo_name}/media"
        try:
            response = await self._get(url, headers=headers, params=params)
            j = response.json()
            return j.get("photoUri")
        except Exception as e:
            logger.warning(f"Failed to resolve photo URI for {photo_name}: {e}")
            return None
    
    async def _build_response_obj(self, place: Dict[str, Any]) -> Dict[str, Any]:
        """Build response object in the format expected by orchestrator"""
        # Extract name with fallback logic
        # IMPORTANT: Google Places API v1 returns "name" as the place_id (e.g., "places/ChIJ...")
        # The actual business name is in "displayName" which can be either a string or dict with "text" key
        display_name = place.get("displayName")
        
        # Extract text from displayName if it's a dict
        if isinstance(display_name, dict):
            name = display_name.get("text") or display_name.get("languageCode") or ""
        elif isinstance(display_name, str):
            name = display_name
        else:
            name = place.get("name")
        
        # Check if name looks like a place_id and fix it
        if name and isinstance(name, str) and (name.startswith("places/") or name.startswith("ChIJ")):
            logger.warning(f"[GOOGLE FETCH] Name field contains place_id: {name}, looking for actual name")
            # Try to get from formatted address as fallback
            name = None
        
        # Handle case where name might be empty string or None
        if not name or (isinstance(name, str) and name.strip() == ""):
            # Last resort: use formatted_address or a default
            formatted_addr = place.get("formattedAddress", "")
            if formatted_addr:
                # Extract first part of address as fallback
                name = formatted_addr.split(",")[0].strip()
            else:
                name = "Business"
            logger.warning(f"[GOOGLE FETCH] Name field was empty, using fallback: {name}")
        
        # Core fields
        out: Dict[str, Any] = {
            "place_id": place.get("id"),
            "name": name,
            "formatted_address": place.get("formattedAddress"),
            "types": place.get("types") or [],
            "primary_type": place.get("primaryType"),
            "website_url": place.get("websiteUri"),
            "google_maps_url": place.get("googleMapsUri"),
            "location": place.get("location"),
            "viewport": place.get("viewport"),
            "contact": {
                "international_phone": place.get("internationalPhoneNumber"),
            },
            "status": {
                "open_now": (place.get("currentOpeningHours") or {}).get("openNow"),
                "weekday_descriptions": (place.get("regularOpeningHours") or {}).get("weekdayDescriptions") or [],
            },
            "rating": place.get("rating"),
            "user_rating_count": place.get("userRatingCount"),
            "price_level": place.get("priceLevel"),
            "editorial_summary": (place.get("editorialSummary") or {}).get("overview"),
            "reviews": [],
            "photos": [],
        }
        
        # Reviews (max 5 available from Places API)
        for rv in (place.get("reviews") or []):
            author_attr = rv.get("authorAttribution") or {}
            out["reviews"].append({
                "rating": rv.get("rating"),
                "text": (rv.get("text") or {}).get("text") if isinstance(rv.get("text"), dict) else rv.get("text", ""),
                "publish_time": rv.get("publishTime"),
                "relative_time": rv.get("relativePublishTimeDescription"),
                "author": author_attr.get("displayName"),
                "author_uri": author_attr.get("uri"),
                "author_photo_uri": author_attr.get("photoUri"),
            })
        
        # Photos: resolve capped number of URIs (each is a separate billable request)
        raw_photos: List[Dict[str, Any]] = place.get("photos") or []
        for p in raw_photos[:MAX_PHOTOS]:
            name = p.get("name")  # e.g., "places/XXX/photos/YYY"
            uri = await self._resolve_photo_uri(name, PHOTO_MAX_WIDTH) if name else None
            out["photos"].append({
                "name": name,
                "width_px": p.get("widthPx"),
                "height_px": p.get("heightPx"),
                "author_attributions": p.get("authorAttributions") or [],
                "download_uri": uri,  # short-lived URL
            })
        
        return out
    
    # Fetches complete place data from Google Places API v1 with photos, reviews, hours, ratings.
    # Returns normalized dict with business_summary fields; handles name extraction bugs (displayName vs name).
    async def fetch_place(self, place_id: str) -> Dict[str, Any]:
        """
        Fetch complete place data from Google Places API v1.
        Returns a dict in the format expected by the orchestrator.
        """
        if not self.api_key:
            raise ApplicationError(
                code=ErrorCode.CONFIGURATION_ERROR,
                message="Google Maps API key not configured. Please set GOOGLE_MAPS_API_KEY in .env file."
            )
        try:
            logger.info(f"[GOOGLE FETCH] Starting fetch_place for place_id: {place_id}")
            
            # Fetch place details
            logger.info("[GOOGLE FETCH] Fetching place details from Places API v1...")
            place_data = await self._fetch_place_details(place_id)
            
            # Log the raw name from API response for debugging
            raw_name = place_data.get("name")
            logger.info(f"[GOOGLE FETCH] Raw API response name field: {repr(raw_name)}")
            
            # Build response object in the expected format
            logger.info("[GOOGLE FETCH] Building response object...")
            response_obj = await self._build_response_obj(place_data)
            
            # Verify name was extracted correctly
            final_name = response_obj.get("name")
            logger.info(f"[GOOGLE FETCH] Final name in response object: {repr(final_name)}")
            
            if not final_name or final_name.strip() == "":
                logger.warning(f"[GOOGLE FETCH] Name is empty in response! Raw response keys: {list(place_data.keys())}")
            
            logger.info("[GOOGLE FETCH] Returning place data")
            return response_obj
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[GOOGLE FETCH] HTTP error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 404:
                raise ApplicationError(
                    code=ErrorCode.INVALID_PLACE_ID,
                    message=f"Place not found: {place_id}",
                    retryable=False
                )
            if e.response.status_code == 429:
                raise ApplicationError(
                    code=ErrorCode.GOOGLE_RATE_LIMIT,
                    message="Google Places API rate limit exceeded",
                    retryable=True
                )
            raise ApplicationError(
                code=ErrorCode.GENERATION_FAILED,
                message=f"Google Places API error: {str(e)}",
                retryable=True
            )
        except Exception as e:
            logger.exception("Unexpected error in fetch_place")
            raise ApplicationError(
                code=ErrorCode.GENERATION_FAILED,
                message=f"Failed to fetch place data: {str(e)}",
                retryable=True
            )


# Global fetcher instance
google_fetcher = GoogleFetcher()
