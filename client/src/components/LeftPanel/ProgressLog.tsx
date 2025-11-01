/**
 * Real-time progress log display via SSE
 * Ref: Product.md > Section 1, lines 38-41
 * SIMPLIFIED: No typing animations, show events immediately
 * Groups events by timestamp (same second) and preserves scroll position
 */

import { useRef, useMemo } from "react";
import type { ProgressEvent } from "../../types/api";
import { PHASE_CONFIG } from "../../utils/phaseConfig";

interface ProgressLogProps {
  events: ProgressEvent[];
}

function ProgressLog({ events }: ProgressLogProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Group events by timestamp (same second) and content type
  const groupedEvents = useMemo(() => {
    if (events.length === 0) return [];

    // Sort events by timestamp (oldest first for grouping)
    const sorted = [...events].sort((a, b) => {
      const aTime = new Date(a.ts).getTime();
      const bTime = new Date(b.ts).getTime();
      return aTime - bTime;
    });

    const groups: Array<ProgressEvent[]> = [];
    let currentGroup: ProgressEvent[] = [];

    for (let i = 0; i < sorted.length; i++) {
      const event = sorted[i];
      
      if (currentGroup.length === 0) {
        // Start new group
        currentGroup.push(event);
      } else {
        const prevEvent = currentGroup[currentGroup.length - 1];
        if (!prevEvent) continue;
        
        const prevTime = new Date(prevEvent.ts);
        const currTime = new Date(event.ts);
        
        // Group if within same second
        const sameSecond = Math.floor(prevTime.getTime() / 1000) === Math.floor(currTime.getTime() / 1000);
        
        if (sameSecond) {
          currentGroup.push(event);
        } else {
          // Save previous group and start new one
          groups.push([...currentGroup]);
          currentGroup = [event];
        }
      }
    }

    // Add final group
    if (currentGroup.length > 0) {
      groups.push(currentGroup);
    }

    // Return in reverse order (newest first for display)
    return groups.reverse();
  }, [events]);

  const latestEvent = events.length > 0 ? events[0] : null;
  const phaseConfig = latestEvent
    ? PHASE_CONFIG[latestEvent.phase] || PHASE_CONFIG.IDLE
    : PHASE_CONFIG.IDLE;

  const formatTimestamp = (ts: string | number) => {
    try {
      const date = typeof ts === 'string' ? new Date(ts) : new Date(ts);
      return date.toLocaleTimeString();
    } catch {
      return "";
    }
  };

  return (
    <div className="p-4 h-full flex flex-col min-h-0">
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <h3 className="text-sm font-semibold text-gray-800">Build Progress</h3>
        {latestEvent && phaseConfig && (
          <div
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${phaseConfig.bgColor} ${phaseConfig.textColor}`}
          >
            {latestEvent.phase !== "ERROR" && latestEvent.phase !== "READY" && (
              <span className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
            )}
            <span>{phaseConfig.icon}</span>
            <span>{phaseConfig.label}</span>
          </div>
        )}
      </div>

      {events.length === 0 ? (
        <div className="flex-1 flex items-center justify-center min-h-0">
          <div className="text-center">
            <div className="text-4xl mb-2">🔍</div>
            <p className="text-gray-500 text-sm">
              Select a business to start building...
            </p>
            <p className="text-gray-400 text-xs mt-1">
              Choose from the search box above
            </p>
          </div>
        </div>
      ) : (
        <div ref={scrollContainerRef} className="space-y-2 overflow-y-auto flex-1 min-h-0">
          {groupedEvents.map((eventGroup, groupIndex) => {
            const primaryEvent = eventGroup[0];
            if (!primaryEvent) return null;
            
            const isError = primaryEvent.phase === "ERROR";
            const groupKey = `group-${groupIndex}-${primaryEvent.ts}`;

            return (
              <div
                key={groupKey}
                className={`text-sm p-3 rounded-lg border ${
                  isError
                    ? "border-red-200 bg-red-50"
                    : "border-gray-200 bg-white hover:shadow-sm transition-shadow"
                }`}
              >
                <div className="flex items-start gap-2">
                  <span className="text-xs text-gray-400 shrink-0">
                    {formatTimestamp(primaryEvent.ts)}
                  </span>
                  <div className="flex-1 min-w-0">
                    {eventGroup.map((event, eventIndex) => {
                      const content = event.detail || event.step || "";
                      const trimmedContent = content.trim().replace(/^\n+|\n+$/g, "");
                      
                      if (!trimmedContent) return null;
                      
                      return (
                        <p
                          key={`${event.ts}-${eventIndex}`}
                          className={`text-xs ${isError ? "text-red-700 font-medium" : "text-gray-700"} ${
                            eventIndex > 0 ? "mt-1" : ""
                          }`}
                      >
                          {trimmedContent}
                      </p>
                      );
                    })}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default ProgressLog;
