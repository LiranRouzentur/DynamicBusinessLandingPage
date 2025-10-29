/**
 * SSE connection hook for real-time progress updates
 * Ref: Product.md lines 728-739 for event format
 */

import { useEffect, useRef } from "react";

interface SSEEvent {
  ts: string;
  session_id: string;
  phase: string;
  step: string;
  detail: string;
  progress: number;
}

export function useSSE(
  sessionId: string | null,
  onEvent: (event: SSEEvent) => void
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
      } catch (error) {
        console.error("[SSE] Failed to parse event:", error);
      }
    };

    eventSource.onerror = (error) => {
      // Connection closed (normal when build completes)
      eventSource.close();
    };

    eventSource.onopen = () => {
      // Connection opened
    };

    return () => {
      eventSource.close();
    };
  }, [sessionId]);
}
