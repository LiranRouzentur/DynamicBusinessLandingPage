"""Normalized place data models - Ref: Product.md > Section 5"""

from typing import List, Optional
from pydantic import BaseModel


class Geometry(BaseModel):
    """Geographic coordinates"""
    lat: float
    lng: float


class OpeningHours(BaseModel):
    """Business operating hours"""
    weekday_text: List[str]


class Place(BaseModel):
    """Normalized place data - Ref: Product.md lines 747-761"""
    place_id: str
    name: str
    types: List[str]
    formatted_address: str
    geometry: Geometry
    website: Optional[str] = None
    formatted_phone_number: Optional[str] = None
    opening_hours: Optional[OpeningHours] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    price_level: Optional[int] = None


class Photo(BaseModel):
    """Place photo data - Ref: Product.md lines 762-770"""
    url: str
    width: int
    height: int
    attribution_html: str
    alt: str


class Review(BaseModel):
    """Place review data - Ref: Product.md lines 771-780"""
    author: str
    avatar: Optional[str] = None
    rating: int
    relative_time: str
    text: str
    language: str


class NormalizedPlacePayload(BaseModel):
    """Complete normalized payload - Ref: Product.md lines 747-781"""
    place: Place
    photos: List[Photo] = []
    reviews: List[Review] = []


class DataRichness(BaseModel):
    """Data availability flags - Ref: Product.md lines 137-142"""
    has_photos: bool
    has_reviews: bool
    has_hours: bool
    has_site: bool


