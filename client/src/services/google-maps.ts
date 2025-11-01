/**
 * Google Maps Places Autocomplete wrapper
 * Optimized with Promise-based loading
 */

let loadPromise: Promise<void> | null = null;

export const initGoogleMaps = (apiKey: string): Promise<void> => {
  // Check if already loaded
  if (window.google && window.google.maps) {
    return Promise.resolve();
  }

  // Return existing promise if already loading
  if (loadPromise) {
    return loadPromise;
  }

  // Check if script tag already exists in DOM
  const existingScript = document.querySelector<HTMLScriptElement>(
    'script[src*="maps.googleapis.com"]'
  );
  
  if (existingScript) {
    // Wait for existing script to load
    loadPromise = new Promise((resolve, reject) => {
      if (window.google && window.google.maps) {
        resolve();
        return;
      }
      
      existingScript.addEventListener('load', () => {
        if (window.google && window.google.maps) {
          resolve();
        } else {
          reject(new Error('Google Maps loaded but API not available'));
        }
      });
      
      existingScript.addEventListener('error', () => {
        reject(new Error('Failed to load Google Maps API'));
      });
    });
    
    return loadPromise;
  }

  // Load Google Maps API with callback
  loadPromise = new Promise((resolve, reject) => {
    const callbackName = '__googleMapsInit';
    
    // Create callback function
    (window as any)[callbackName] = () => {
      delete (window as any)[callbackName];
      resolve();
    };

    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places&loading=async&callback=${callbackName}`;
    script.async = true;
    script.defer = true;
    
    script.onerror = () => {
      delete (window as any)[callbackName];
      loadPromise = null;
      reject(new Error("Failed to load Google Maps API"));
    };
    
    document.head.appendChild(script);
  });

  return loadPromise;
};
