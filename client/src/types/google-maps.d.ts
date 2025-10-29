/**
 * Google Maps API TypeScript declarations
 */

interface Window {
  google?: typeof google;
  __googleMapsInit?: () => void;
}

declare namespace google {
  namespace maps {
    namespace places {
      interface AutocompleteOptions {
        types?: string[];
        fields?: string[];
      }

      class Autocomplete {
        constructor(
          inputField: HTMLElement | HTMLInputElement | null,
          opts?: AutocompleteOptions
        );
        getPlace(): PlaceResult;
        addListener(eventName: string, handler: () => void): void;
      }

      // Modern PlaceAutocompleteElement
      class PlaceAutocompleteElement extends HTMLElement {
        // Note: types property is not available in this version of the API
        componentRestrictions?: { country?: string | string[] };
        addEventListener(
          type: "gmp-placeselect",
          listener: (event: CustomEvent<{ place: PlaceResult }>) => void
        ): void;
        addEventListener(
          type: "gmp-error",
          listener: (event: CustomEvent<Error>) => void
        ): void;
      }

      interface PlaceResult {
        id?: string;
        place_id?: string;
        name?: string;
        formatted_address?: string;
        types?: string[];
        geometry?: {
          location?: {
            lat(): number;
            lng(): number;
          };
        };
      }
    }

    namespace event {
      function clearInstanceListeners(instance: any): void;
    }
  }
}
