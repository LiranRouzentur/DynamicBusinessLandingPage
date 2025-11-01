/**
 * Phase configuration for build progress display
 */

export interface PhaseConfig {
  icon: string;
  color: string;
  bgColor: string;
  textColor: string;
  label: string;
}

export const PHASE_CONFIG: Record<string, PhaseConfig> = {
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

