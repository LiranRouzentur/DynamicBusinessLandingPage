/**
 * Left Panel Component - Ref: Product.md > Section 1, lines 38-41
 *
 * Top Area (30% height): Google Maps Autocomplete
 * Bottom Area (70% height): Real-time progress log via SSE
 */

import { useEffect, useState } from "react";
import SearchBox from "./SearchBox";
import ProgressLog from "./ProgressLog";
import { useSSE } from "../../hooks/useSSE";

interface LeftPanelProps {
  onSessionStart: (sessionId: string) => void;
  sessionId: string | null;
  onReady: (ready: boolean) => void;
}

function LeftPanel({ onSessionStart, sessionId, onReady }: LeftPanelProps) {
  const [progressEvents, setProgressEvents] = useState<any[]>([]);

  // Connect to SSE when session starts
  useSSE(sessionId, (event) => {
    setProgressEvents((prev) => {
      const newEvents = [event, ...prev]; // Add new event at the START of the array
      return newEvents;
    });

    // Check if build is ready
    if (event.phase === "READY") {
      onReady(true);
    }
  });

  const handlePlaceSelect = (placeId: string) => {
    if (!placeId) {
      alert("Error: Place ID is missing. Please try selecting again.");
      return;
    }

    try {
      fetch("/api/build", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ place_id: placeId }),
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(
              `API request failed: ${response.status} ${response.statusText}`
            );
          }
          return response.json();
        })
        .then((data) => {
          onSessionStart(data.session_id);
          setProgressEvents([]); // Reset progress log
          onReady(false); // Reset ready state
        })
        .catch((error) => {
          console.error("[LeftPanel] Failed to start build:", error);
          alert(
            "Failed to start building landing page. Please check console for details."
          );
        });
    } catch (error) {
      console.error("Failed to start build:", error);
      alert(
        "Failed to start building landing page. Please check console for details."
      );
    }
  };

  const handleTestBuild = () => {
    console.log("[LeftPanel] Test button clicked");
    handlePlaceSelect("ChIJN1t_tDeuEmsRUsoyG83frY4"); // Sydney Opera House for testing
  };

  return (
    <div className="flex flex-col h-full">
      {/* Top: Search Box */}
      <div className="h-[30%] p-4 border-b border-gray-200">
        <SearchBox onPlaceSelect={handlePlaceSelect} />
        <button
          onClick={handleTestBuild}
          className="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          🧪 Test Build (Force)
        </button>
      </div>

      {/* Bottom: Progress Log */}
      <div className="h-[70%] overflow-y-auto">
        <ProgressLog events={progressEvents} />
      </div>
    </div>
  );
}

export default LeftPanel;
