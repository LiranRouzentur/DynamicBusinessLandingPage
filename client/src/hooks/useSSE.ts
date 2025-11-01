/**
 * SSE connection hook for real-time progress updates
 * Ref: Product.md lines 728-739 for event format
 */

import { useEffect, useRef } from "react";
import type { ProgressEvent } from "../types/api";
import { logger } from "../utils/logger";

export function useSSE(
  sessionId: string | null,
  onEvent: (event: ProgressEvent) => void
) {
  const onEventRef = useRef(onEvent);

  // Keep the callback ref in sync
  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    if (!sessionId) return;

    // Connect to SSE stream
    const eventSource = new EventSource(`/sse/progress/${sessionId}`);

    eventSource.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        onEventRef.current(event);
        
        // Check if build reached terminal state (READY or ERROR)
        if (event.phase === "READY" || event.phase === "ERROR") {
          logger.log(`[SSE] Terminal state reached: ${event.phase}, closing connection`);
          // Close connection after a short delay to ensure all events are processed
          setTimeout(() => {
            eventSource.close();
            logger.log("[SSE] Connection closed");
          }, 1000); // 1 second delay
        }
      } catch (error) {
        logger.error("[SSE] Failed to parse event:", error);
      }
    };

    eventSource.onerror = (error) => {
      logger.error("[SSE] Connection error:", error);
      // Only close if connection is actually closed (not just a temporary error)
      if (eventSource.readyState === EventSource.CLOSED) {
        logger.log("[SSE] Connection closed by server");
      eventSource.close();
      }
    };

    eventSource.onopen = () => {
      // Connection opened
    };

    return () => {
      eventSource.close();
    };
  }, [sessionId]);
}
