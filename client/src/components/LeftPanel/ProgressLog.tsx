/**
 * Real-time progress log display via SSE
 * Ref: Product.md > Section 1, lines 38-41
 */

import { useEffect, useRef } from "react";

interface ProgressEvent {
  ts: string;
  session_id: string;
  phase: string;
  step: string;
  detail: string;
  progress: number;
}

interface ProgressLogProps {
  events: ProgressEvent[];
}

// Phase configuration with icons, colors, and labels
const PHASE_CONFIG: Record<
  string,
  {
    icon: string;
    color: string;
    bgColor: string;
    textColor: string;
    label: string;
  }
> = {
  IDLE: {
    icon: "⏸️",
    color: "gray",
    bgColor: "bg-gray-100",
    textColor: "text-gray-700",
    label: "Idle",
  },
  FETCHING: {
    icon: "📥",
    color: "blue",
    bgColor: "bg-blue-50",
    textColor: "text-blue-700",
    label: "Fetching Data",
  },
  ORCHESTRATING: {
    icon: "🎯",
    color: "purple",
    bgColor: "bg-purple-50",
    textColor: "text-purple-700",
    label: "Orchestrating",
  },
  GENERATING: {
    icon: "⚡",
    color: "yellow",
    bgColor: "bg-yellow-50",
    textColor: "text-yellow-700",
    label: "Generating",
  },
  QA: {
    icon: "✅",
    color: "green",
    bgColor: "bg-green-50",
    textColor: "text-green-700",
    label: "Quality Assurance",
  },
  READY: {
    icon: "🎉",
    color: "emerald",
    bgColor: "bg-emerald-50",
    textColor: "text-emerald-700",
    label: "Ready",
  },
  ERROR: {
    icon: "❌",
    color: "red",
    bgColor: "bg-red-50",
    textColor: "text-red-700",
    label: "Error",
  },
};

function ProgressLog({ events }: ProgressLogProps) {
  const endRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const getLatestEvent = () => {
    // Events are added to the START of the array, so the first event is the latest
    return events.length > 0 ? events[0] : null;
  };

  const latestEvent = getLatestEvent();
  console.log("[ProgressLog] Latest event:", latestEvent);
  console.log("[ProgressLog] Latest event phase:", latestEvent?.phase);

  const phaseConfig = latestEvent
    ? PHASE_CONFIG[latestEvent.phase] || PHASE_CONFIG.IDLE
    : null;

  console.log("[ProgressLog] Phase config:", phaseConfig);

  const formatTimestamp = (ts: string) => {
    try {
      const date = new Date(ts);
      return date.toLocaleTimeString();
    } catch {
      return "";
    }
  };

  return (
    <div className="p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
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
        <div className="flex-1 flex items-center justify-center">
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
        <div className="space-y-2 overflow-y-auto flex-1">
          {events.map((event, index) => {
            const config = PHASE_CONFIG[event.phase] || PHASE_CONFIG.IDLE;
            const isError = event.phase === "ERROR";
            // Each event creates a new log entry
            const eventKey = `${index}-${event.ts}`;

            return (
              <div
                key={eventKey}
                className={`text-sm p-3 rounded-lg border ${
                  isError
                    ? "border-red-200 bg-red-50"
                    : "border-gray-200 bg-white hover:shadow-sm transition-shadow"
                }`}
              >
                <div className="flex items-start gap-2">
                  <span className="text-xs text-gray-400 shrink-0">
                    {formatTimestamp(event.ts)}
                  </span>
                  <div className="flex-1 min-w-0">
                    {event.detail ? (
                      <p
                        className={`text-xs ${isError ? "text-red-700 font-medium" : "text-gray-700"}`}
                      >
                        {event.detail}
                      </p>
                    ) : event.step ? (
                      <p
                        className={`text-xs ${isError ? "text-red-700 font-medium" : "text-gray-700"}`}
                      >
                        {event.step}
                      </p>
                    ) : null}
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
