/**
 * Iframe container for generated landing page
 * Ref: Product.md > Section 1, line 43
 */

import { useState } from "react";

interface SiteFrameProps {
  sessionId: string | null;
  isReady?: boolean;
}

function SiteFrame({ sessionId, isReady = false }: SiteFrameProps) {
  const [hasError, setHasError] = useState(false);

  if (!sessionId) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-500">
          No page generated yet. Select a business to begin.
        </p>
      </div>
    );
  }

  if (!isReady) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-500">
          Building your landing page... This may take a moment.
        </p>
      </div>
    );
  }

  if (hasError) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center p-8">
          <p className="text-red-600 text-lg font-semibold mb-2">
            Failed to load the landing page
          </p>
          <p className="text-gray-600 text-sm">
            The generated page could not be displayed.
          </p>
          <button
            onClick={() => {
              setHasError(false);
              window.location.reload();
            }}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full bg-white">
      <iframe
        src={`/api/result/${sessionId}`}
        className="w-full h-full border-0"
        title="Generated Landing Page"
        loading="eager"
        style={{ minHeight: "100%" }}
        onError={() => setHasError(true)}
        onLoad={() => setHasError(false)}
      />
    </div>
  );
}

export default SiteFrame;
