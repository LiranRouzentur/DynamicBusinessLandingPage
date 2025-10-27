/**
 * Google Maps Places Autocomplete wrapper
 * Uses modern PlaceAutocompleteElement as recommended by Google
 */

let isLoading = false;
let isLoaded = false;

export const initGoogleMaps = (apiKey: string) => {
  // Check if already loaded
  if (window.google && window.google.maps) {
    isLoaded = true;
    return Promise.resolve();
  }

  // Check if already loading
  if (isLoading) {
    return new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        if (isLoaded) {
          clearInterval(checkInterval);
          resolve();
        }
      }, 100);
    });
  }

  // Check if script tag already exists in DOM
  const existingScript = document.querySelector(
    'script[src*="maps.googleapis.com"]'
  );
  if (existingScript) {
    isLoading = true;
    return new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        if (window.google && window.google.maps) {
          isLoaded = true;
          isLoading = false;
          clearInterval(checkInterval);
          resolve();
        }
      }, 100);
    });
  }

  // Load Google Maps API asynchronously with callback
  isLoading = true;
  const script = document.createElement("script");
  script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places&loading=async&callback=__googleMapsInit`;

  // Create callback function
  window.__googleMapsInit = () => {
    isLoaded = true;
    isLoading = false;
  };

  return new Promise((resolve, reject) => {
    script.onload = () => {
      // Wait for the callback to fire
      const checkInterval = setInterval(() => {
        if (isLoaded) {
          clearInterval(checkInterval);
          resolve();
        }
      }, 100);
    };
    script.onerror = () => {
      isLoading = false;
      reject(new Error("Failed to load Google Maps API"));
    };
    document.head.appendChild(script);
  });
};
