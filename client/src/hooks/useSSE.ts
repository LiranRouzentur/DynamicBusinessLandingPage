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

    console.log("SSE: Connecting to session:", sessionId);

    // Connect to SSE stream
    const eventSource = new EventSource(`/sse/progress/${sessionId}`);

    eventSource.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        console.log("SSE: Received event:", event);
        onEventRef.current(event);
      } catch (error) {
        console.error("Failed to parse SSE event:", error);
      }
    };

    eventSource.onerror = (error) => {
      console.error("SSE error:", error);
      eventSource.close();
    };

    eventSource.onopen = () => {
      console.log("SSE: Connection opened for session:", sessionId);
    };

    return () => {
      console.log("SSE: Closing connection for session:", sessionId);
      eventSource.close();
    };
  }, [sessionId]);
}
