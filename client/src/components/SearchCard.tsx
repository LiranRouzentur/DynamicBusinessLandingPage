/**
 * Search Card Component
 * Reusable card that transitions from center to top-left panel
 */

import { useEffect, useRef, useState } from "react";
import { initGoogleMaps } from "../services/google-maps";
import { GOOGLE_MAPS_API_KEY } from "../utils/constants";
import { logger } from "../utils/logger";

interface SearchCardProps {
  onPlaceSelect: (placeId: string) => void;
  isInPanel?: boolean;
}

function SearchCard({ onPlaceSelect, isInPanel = false }: SearchCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const autocompleteRef = useRef<google.maps.places.Autocomplete | null>(null);
  const [isGoogleLoaded, setIsGoogleLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize Google Maps API
  useEffect(() => {
    if (GOOGLE_MAPS_API_KEY) {
      initGoogleMaps(GOOGLE_MAPS_API_KEY)
        .then(() => {
          setIsGoogleLoaded(true);
        })
        .catch((error) => {
          logger.error("[SearchCard] Failed to initialize Google Maps:", error);
          setError("Failed to load Google Maps");
        });
    } else {
      logger.warn("[SearchCard] Google Maps API key not configured");
      setError("Google Maps API key not configured");
    }
  }, []);

  // Initialize Autocomplete when Google Maps is loaded
  useEffect(() => {
    if (!isGoogleLoaded || !inputRef.current || autocompleteRef.current) {
      return undefined;
    }

    try {
      const autocomplete = new window.google.maps.places.Autocomplete(
        inputRef.current,
        {
          types: ["establishment"],
          fields: ["place_id", "name", "formatted_address", "geometry"],
        }
      );

      autocompleteRef.current = autocomplete;

      autocomplete.addListener("place_changed", () => {
        const place = autocomplete.getPlace();

        if (place && place.place_id) {
          onPlaceSelect(place.place_id);
        } else {
          logger.error("[SearchCard] Invalid place selection");
        }
      });

      return () => {
        if (autocompleteRef.current) {
          autocompleteRef.current = null;
        }
      };
    } catch (error) {
      logger.error("[SearchCard] Error initializing Autocomplete:", error);
      setError("Failed to initialize search");
      return undefined;
    }
  }, [isGoogleLoaded, onPlaceSelect]);

  return (
    <div
      className={`bg-white rounded-lg shadow-lg transition-all duration-700 ease-in-out ${
        isInPanel ? "py-4 shadow-md" : "p-8 shadow-lg"
      }`}
      style={{
        paddingLeft: isInPanel ? "1rem" : undefined,
        paddingRight: isInPanel ? "1rem" : undefined,
      }}
    >
      {/* Logo Image - Disappears smoothly when transitioning to panel */}
      <div
        className={`flex justify-center transition-all duration-700 ease-in-out overflow-hidden ${
          isInPanel ? "opacity-0 h-0" : "opacity-100 h-auto mb-6"
        }`}
      >
        <img
          src="/assets/images/logo.png"
          alt="Dynamic Business Landing Page"
          className="object-contain transition-all duration-700 ease-in-out"
          style={{
            width: isInPanel ? "0%" : "50%",
            height: "auto",
          }}
          onError={(e) => {
            logger.warn("[SearchCard] Logo image not found");
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      </div>

      {/* Search Input Field */}
      <div className="w-full transition-all duration-700">
        <input
          ref={inputRef}
          autoFocus={true}
          type="text"
          placeholder="Search for a business..."
          className={`w-full px-4 bg-white text-gray-900 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-700 ${
            isInPanel ? "py-2" : "py-3"
          }`}
        />
        {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
      </div>
    </div>
  );
}

export default SearchCard;
