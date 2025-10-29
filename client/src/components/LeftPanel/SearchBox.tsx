/**
 * Google Maps Autocomplete Search Box
 * Ref: Product.md > Section 1, lines 38-41
 * Uses classic Autocomplete API for better reliability
 */

import { useEffect, useRef, useState } from "react";
import { initGoogleMaps } from "../../services/google-maps";
import { GOOGLE_MAPS_API_KEY } from "../../utils/constants";

interface SearchBoxProps {
  onPlaceSelect: (placeId: string) => void;
}

function SearchBox({ onPlaceSelect }: SearchBoxProps) {
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
          console.error("[SearchBox] Failed to initialize Google Maps:", error);
          setError("Failed to load Google Maps");
        });
    } else {
      console.warn("[SearchBox] Google Maps API key not configured");
      setError("Google Maps API key not configured");
    }
  }, []);

  // Initialize Autocomplete when Google Maps is loaded
  useEffect(() => {
    if (!isGoogleLoaded || !inputRef.current || autocompleteRef.current) {
      return;
    }

    try {
      // Create the Autocomplete instance (classic API)
      // Note: google.maps.places.Autocomplete is deprecated but still functional
      // Future: migrate to PlaceAutocompleteElement when needed
      const autocomplete = new window.google.maps.places.Autocomplete(
        inputRef.current,
        {
          types: ["establishment"],
          fields: ["place_id", "name", "formatted_address", "geometry"],
        }
      );

      autocompleteRef.current = autocomplete;

      // Add event listener for when a place is selected
      autocomplete.addListener("place_changed", () => {
        const place = autocomplete.getPlace();

        if (place && place.place_id) {
          onPlaceSelect(place.place_id);
        } else {
          console.error("[SearchBox] Invalid place selection");
        }
      });

      // Cleanup
      return () => {
        if (autocompleteRef.current) {
          autocompleteRef.current = null;
        }
      };
    } catch (error) {
      console.error("[SearchBox] Error initializing Autocomplete:", error);
      setError("Failed to initialize search");
    }
  }, [isGoogleLoaded]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="w-full">
      <h2 className="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">
        Search Business
      </h2>
      <input
        ref={inputRef}
        type="text"
        placeholder="Search for a business..."
        className="w-full px-4 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      />
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400 mt-2">{error}</p>
      )}
      {!GOOGLE_MAPS_API_KEY && (
        <p className="text-sm text-yellow-600 dark:text-yellow-400 mt-2">
          Google Maps API key not configured
        </p>
      )}
    </div>
  );
}

export default SearchBox;
