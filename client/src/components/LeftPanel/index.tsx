/**
 * Left Panel Component - Progress log display
 * Shows real-time build progress via SSE
 */

import { useState, useEffect, useCallback } from "react";
import ProgressLog from "./ProgressLog";
import { useSSE } from "../../hooks/useSSE";
import { useBuild } from "../../contexts/BuildContext";
import type { ProgressEvent } from "../../types/api";

interface LeftPanelProps {
  placeSelected: boolean;
}

// Helper function to normalize event text for comparison
const normalizeEventText = (text: string | undefined): string => {
  if (!text) return "";
  return text.trim().replace(/\s+/g, " ");
};

// Helper function to create a unique key for an event (timestamp + phase + FULL text)
const getEventKey = (e: ProgressEvent): string => {
  const text = normalizeEventText(e.detail || e.step || "");
  // Use FULL text for maximum uniqueness (no substring)
  return `${e.session_id}-${e.ts}-${e.phase}-${text}`;
};

function LeftPanel({ placeSelected }: LeftPanelProps) {
  const { sessionId, setIsReady } = useBuild();
  const [progressEvents, setProgressEvents] = useState<ProgressEvent[]>([]);

  // Memoize event handler to prevent unnecessary SSE reconnections
  const handleSSEEvent = useCallback((event: ProgressEvent) => {
    setProgressEvents((prev) => {
      // Normalize and check if this event already exists (deduplicate based on timestamp + normalized text)
      const eventKey = getEventKey(event);
      const exists = prev.some(e => getEventKey(e) === eventKey);
      
      if (exists) {
        // Event already exists - don't add duplicate
        return prev;
      }
      
      // Add new event and sort by timestamp (newest first / descending order)
      // ts is a string (ISO format), convert to number for comparison
      const updated = [event, ...prev];
      return updated.sort((a, b) => {
        const aTs = new Date(a.ts).getTime();
        const bTs = new Date(b.ts).getTime();
        return bTs - aTs; // Descending order (newest first)
      });
    });

    // Check if build is ready
    if (event.phase === "READY") {
      setIsReady(true);
    }
  }, [setIsReady]);

  // Connect to SSE when session starts
  useSSE(sessionId, handleSSEEvent);

  // Reset progress log and ready flag when a new session starts
  useEffect(() => {
    setProgressEvents([]);
    setIsReady(false);
  }, [sessionId, setIsReady]);

  // Only show in expanded layout
  if (!placeSelected) {
    return null;
  }

  return (
    <div className="flex flex-col h-full animate-fade-in">
      {/* Progress Log */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <ProgressLog events={progressEvents} />
      </div>
    </div>
  );
}

export default LeftPanel;
