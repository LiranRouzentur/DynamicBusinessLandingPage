/**
 * Custom hook for build API calls
 * Centralizes error handling and state management
 */

import { useCallback, useState } from "react";
import { useBuild } from "../contexts/BuildContext";

interface UseBuildApiReturn {
  startBuild: (placeId: string) => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

export function useBuildApi(): UseBuildApiReturn {
  const { setSessionId } = useBuild();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startBuild = useCallback(
    async (placeId: string) => {
      if (!placeId) {
        setError("Place ID is missing. Please try selecting again.");
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch("/api/build", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ place_id: placeId }),
        });

        if (!response.ok) {
          throw new Error(
            `API request failed: ${response.status} ${response.statusText}`
          );
        }

        const data = await response.json();
        setSessionId(data.session_id);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to start build";
        console.error("[useBuildApi] Failed to start build:", err);
        setError(errorMessage);
      } finally {
        setIsLoading(false);
      }
    },
    [setSessionId]
  );

  return { startBuild, isLoading, error };
}

