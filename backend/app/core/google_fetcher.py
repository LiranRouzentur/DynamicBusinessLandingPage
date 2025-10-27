"""Google Maps API client - Product.md > Section 2, lines 63-85"""

from typing import Optional, List, Dict, Any
import googlemaps
from app.core.config import settings
from app.models.normalized_data import (
    NormalizedPlacePayload,
    Place,
    Photo,
    Review,
    Geometry,
    OpeningHours
)
from app.models.errors import ApplicationError, ErrorCode
import asyncio


class GoogleFetcher:
    """
    Fetches Place Details, Photos, Reviews from Google Maps API.
    
    Uses the most efficient methods:
    - Place Details API
    - Place Photos API  
    - Place Reviews
    """
    
    def __init__(self):
        if not settings.google_maps_api_key:
            print("WARNING: GOOGLE_MAPS_API_KEY not set in .env file")
        self.client = googlemaps.Client(key=settings.google_maps_api_key) if settings.google_maps_api_key else None
    
    async def fetch_place(self, place_id: str) -> NormalizedPlacePayload:
        """
        Fetch complete place data from Google Maps API.
        
        Ref: Product.md lines 63-85
        Normalized payload structure defined in Product.md lines 747-782
        """
        if self.client is None:
            raise ApplicationError(
                code=ErrorCode.CONFIGURATION_ERROR,
                message="Google Maps API key not configured. Please set GOOGLE_MAPS_API_KEY in .env file."
            )
        try:
            print(f"[FETCHER] Starting fetch_place for place_id: {place_id}")
            # Fetch place details
            print(f"[FETCHER] Calling _fetch_place_details...")
            place_details = await asyncio.to_thread(
                self._fetch_place_details,
                place_id
            )
            print(f"[FETCHER] _fetch_place_details returned")
            
            # Extract photos
            print(f"[FETCHER] Extracting photos...")
            photos = self._extract_photos(place_details)
            print(f"[FETCHER] Extracted {len(photos)} photos")
            
            # Extract reviews (already in place_details)
            print(f"[FETCHER] Extracting reviews...")
            reviews = self._extract_reviews(place_details)
            print(f"[FETCHER] Extracted {len(reviews)} reviews")
            
            # Build normalized place object
            print(f"[FETCHER] Building normalized place object...")
            place = self._build_place_object(place_details)
            print(f"[FETCHER] Place object built: {place.name}")
            
            # Build opening hours
            opening_hours = self._build_opening_hours(place_details)
            if opening_hours:
                place.opening_hours = opening_hours
            
            payload = NormalizedPlacePayload(
                place=place,
                photos=photos,
                reviews=reviews
            )
            print(f"[FETCHER] Returning NormalizedPlacePayload")
            return payload
            
        except googlemaps.exceptions.ApiError as e:
            print(f"[FETCHER] Google Maps API error: {e}")
            if "INVALID_REQUEST" in str(e) or "NOT_FOUND" in str(e):
                raise ApplicationError(
                    code=ErrorCode.INVALID_PLACE_ID,
                    message=f"Invalid place_id: {place_id}",
                    retryable=False
                )
            raise ApplicationError(
                code=ErrorCode.GOOGLE_RATE_LIMIT,
                message=f"Google Maps API error: {str(e)}",
                retryable=True
            )
        except Exception as e:
            print(f"[FETCHER] Unexpected error in fetch_place: {e}")
            import traceback
            print(traceback.format_exc())
            raise ApplicationError(
                code=ErrorCode.GENERATION_FAILED,
                message=f"Failed to fetch place data: {str(e)}",
                retryable=True
            )
    
    def _fetch_place_details(self, place_id: str) -> Dict[str, Any]:
        """Fetch place details from Google Maps"""
        return self.client.place(
            place_id=place_id,
            fields=[
                "name", "type", "formatted_address", "geometry",
                "website", "formatted_phone_number", "opening_hours",
                "rating", "user_ratings_total", "price_level",
                "photo", "reviews"
            ]
        )
    
    def _build_place_object(self, details: Dict[str, Any]) -> Place:
        """Build Place object from Google Maps response"""
        result = details.get("result", {})
        geometry = result.get("geometry", {}).get("location", {})
        
        return Place(
            place_id=details.get("place_id", ""),
            name=result.get("name", ""),
            types=result.get("types", []),
            formatted_address=result.get("formatted_address", ""),
            geometry=Geometry(
                lat=geometry.get("lat", 0),
                lng=geometry.get("lng", 0)
            ),
            website=result.get("website"),
            formatted_phone_number=result.get("formatted_phone_number"),
            rating=result.get("rating"),
            user_ratings_total=result.get("user_ratings_total"),
            price_level=result.get("price_level")
        )
    
    def _extract_photos(self, details: Dict[str, Any]) -> List[Photo]:
        """Extract and process photos from place details"""
        photos = []
        result = details.get("result", {})
        photo_data = result.get("photo", [])
        
        for idx, photo in enumerate(photo_data[:8]):  # Limit to 8 photos
            photo_ref = photo.get("photo_reference")
            if not photo_ref:
                continue
            
            # Build photo URL
            photo_url = self._get_photo_url(
                photo_ref,
                maxwidth=800,
                maxheight=600
            )
            
            photos.append(Photo(
                url=photo_url,
                width=photo.get("width", 800),
                height=photo.get("height", 600),
                attribution_html=photo.get("html_attributions", [""])[0] if photo.get("html_attributions") else "",
                alt=f"{result.get('name', 'Business')} - Photo {idx + 1}"
            ))
        
        return photos
    
    def _get_photo_url(self, photo_reference: str, maxwidth: int = 800, maxheight: int = 600) -> str:
        """Get photo URL from photo reference"""
        return f"https://maps.googleapis.com/maps/api/place/photo?maxwidth={maxwidth}&photo_reference={photo_reference}&key={settings.google_maps_api_key}"
    
    def _extract_reviews(self, details: Dict[str, Any]) -> List[Review]:
        """Extract reviews from place details"""
        reviews = []
        result = details.get("result", {})
        review_data = result.get("reviews", [])
        
        for review in review_data[:6]:  # Limit to 6 reviews
            reviews.append(Review(
                author=review.get("author_name", ""),
                avatar=None,  # Not provided by API
                rating=review.get("rating", 0),
                relative_time=review.get("relative_time_description", ""),
                text=review.get("text", ""),
                language=review.get("language", "en")
            ))
        
        return reviews
    
    def _build_opening_hours(self, details: Dict[str, Any]) -> Optional[OpeningHours]:
        """Build OpeningHours object"""
        result = details.get("result", {})
        opening_hours = result.get("opening_hours")
        
        if not opening_hours or not opening_hours.get("weekday_text"):
            return None
        
        return OpeningHours(
            weekday_text=opening_hours.get("weekday_text", [])
        )


# Global fetcher instance
google_fetcher = GoogleFetcher()

