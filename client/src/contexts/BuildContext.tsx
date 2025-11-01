/**
 * Build Context - Centralized state management for build session
 * Eliminates prop drilling and reduces re-renders
 */

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

interface BuildContextValue {
  sessionId: string | null;
  isReady: boolean;
  setSessionId: (id: string | null) => void;
  setIsReady: (ready: boolean) => void;
}

const BuildContext = createContext<BuildContextValue | undefined>(undefined);

export function BuildProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  const handleSetSessionId = useCallback((id: string | null) => {
    setSessionId(id);
    // Reset ready state when session changes
    if (id !== sessionId) {
      setIsReady(false);
    }
  }, [sessionId]);

  const handleSetIsReady = useCallback((ready: boolean) => {
    setIsReady(ready);
  }, []);

  return (
    <BuildContext.Provider
      value={{
        sessionId,
        isReady,
        setSessionId: handleSetSessionId,
        setIsReady: handleSetIsReady,
      }}
    >
      {children}
    </BuildContext.Provider>
  );
}

export function useBuild() {
  const context = useContext(BuildContext);
  if (context === undefined) {
    throw new Error("useBuild must be used within a BuildProvider");
  }
  return context;
}

