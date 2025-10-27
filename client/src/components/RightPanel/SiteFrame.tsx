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

  return (
    <iframe
      src={`/api/result/${sessionId}`}
      className="w-full h-full border-0"
      title="Generated Landing Page"
      loading="lazy"
      onError={() => setHasError(true)}
      onLoad={() => setHasError(false)}
    />
  );
}

export default SiteFrame;
