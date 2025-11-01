/**
 * Main application component
 * Ref: Product.md > Section 1, lines 36-43
 *
 * Layout:
 * - Initial: Centered Google Places Autocomplete input
 * - After selection: Horizontal split (30/70)
 *   - Left Panel: Search and progress log
 *   - Right Panel: Generated landing page in iframe
 */

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import LeftPanel from "./components/LeftPanel";
import SiteFrame from "./components/RightPanel/SiteFrame";
import SearchCard from "./components/SearchCard";
import { useBuildApi } from "./hooks/useBuildApi";
import { useDebounce } from "./hooks/useDebounce";

function App() {
  const { startBuild, error: buildError } = useBuildApi();
  const [hasSelectedPlace, setHasSelectedPlace] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);
  const [cardHeight, setCardHeight] = useState<number | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const cardInnerRef = useRef<HTMLDivElement>(null);
  
  // Debounce cardHeight updates to reduce re-renders
  const debouncedCardHeight = useDebounce(cardHeight, 100);

  // Check if desktop viewport with debouncing
  useEffect(() => {
    let timeoutId: number | undefined;
    
    const checkDesktop = () => {
      if (timeoutId !== undefined) {
        clearTimeout(timeoutId);
      }
      timeoutId = window.setTimeout(() => {
        setIsDesktop(window.innerWidth >= 768);
      }, 150); // Debounce resize events
    };
    
    checkDesktop();
    window.addEventListener("resize", checkDesktop);
    return () => {
      window.removeEventListener("resize", checkDesktop);
      if (timeoutId !== undefined) {
        clearTimeout(timeoutId);
      }
    };
  }, []);

  // Measure card height when it's in panel mode
  useEffect(() => {
    if (hasSelectedPlace && cardInnerRef.current) {
      const updateHeight = () => {
        // Use requestAnimationFrame to ensure DOM has updated
        requestAnimationFrame(() => {
          const height = cardInnerRef.current?.offsetHeight;
          if (height && height > 0) {
            setCardHeight(height);
          }
        });
      };

      // Initial measurement with delay to ensure transition has started
      const timeout = window.setTimeout(updateHeight, 100);

      // Update on resize
      const resizeObserver = new ResizeObserver(() => {
        updateHeight();
      });

      if (cardInnerRef.current) {
        resizeObserver.observe(cardInnerRef.current);
      }

      return () => {
        clearTimeout(timeout);
        resizeObserver.disconnect();
      };
    }
    
    setCardHeight(null);
  }, [hasSelectedPlace]);

  const handlePlaceSelect = useCallback(async (placeId: string) => {
    if (!placeId) {
      alert("Error: Place ID is missing. Please try selecting again.");
      return;
    }

    // Trigger transition immediately
    setHasSelectedPlace(true);

    await startBuild(placeId);
    
    if (buildError) {
      alert(buildError);
      setHasSelectedPlace(false);
    }
  }, [startBuild, buildError]);

  // Memoize style calculations
  const cardContainerStyle = useMemo(() => ({
    top: hasSelectedPlace ? "0" : "50%",
    left: hasSelectedPlace ? "0" : "50%",
    transform: hasSelectedPlace
      ? "translate(0, 0)"
      : "translate(-50%, -50%)",
    width: "100%",
    maxWidth: hasSelectedPlace
      ? isDesktop
        ? "30vw"
        : "100%"
      : "42rem",
    paddingLeft: hasSelectedPlace ? "0" : "1.5rem",
    paddingRight: hasSelectedPlace ? "0" : "1.5rem",
    transition: "all 0.7s cubic-bezier(0.4, 0, 0.2, 1)",
    zIndex: hasSelectedPlace ? 40 : 50,
  }), [hasSelectedPlace, isDesktop]);

  const spacerStyle = useMemo(() => ({
    height: debouncedCardHeight ? `${debouncedCardHeight}px` : undefined,
    minHeight: debouncedCardHeight ? undefined : "30%",
  }), [debouncedCardHeight]);

  return (
    <div className="h-screen bg-gray-50 overflow-hidden relative">
      {/* Search Card - Single instance that transitions smoothly */}
      <div
        ref={cardRef}
        className="fixed transition-all duration-700 ease-in-out"
        style={cardContainerStyle}
      >
        <div ref={cardInnerRef} className="relative">
          <SearchCard
            onPlaceSelect={handlePlaceSelect}
            isInPanel={hasSelectedPlace}
          />
        </div>
      </div>

      {/* Expanded Layout View */}
      <div
        className={`flex flex-col md:flex-row h-full transition-all duration-700 ease-in-out ${
          hasSelectedPlace
            ? "opacity-100 translate-y-0 animate-layout-expand"
            : "opacity-0 translate-y-4 pointer-events-none absolute inset-0"
        }`}
      >
        {/* Left Panel - Contains progress log */}
        <div className="w-full md:w-[30%] flex flex-col border-r border-b md:border-b-0 border-gray-200 relative">
          {/* Spacer for search card - matches actual card height, ensures logs don't hide */}
          <div
            className="border-b border-gray-200 flex-shrink-0"
            style={spacerStyle}
          />

          {/* Progress log area - starts below the search card spacer */}
          <div className="flex-1 overflow-hidden min-h-0">
            <LeftPanel placeSelected={hasSelectedPlace} />
          </div>
        </div>

        {/* Right Panel - 70% width on desktop, full width on mobile */}
        <div className="w-full md:w-[70%] flex-1 animate-panel-slide-in-right">
          <SiteFrame />
        </div>
      </div>
    </div>
  );
}

export default App;
