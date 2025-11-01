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
    // SPDX-License-Identifier: Proprietary
    // Copyright © 2025 Liran Rouzentur. All rights reserved.
    // כל הזכויות שמורות © 2025 לירן רויזנטור.
    // קוד זה הינו קנייני וסודי. אין להעתיק, לערוך, להפיץ או לעשות בו שימוש ללא אישור מפורש.
    // © 2025 Лиран Ройзентур. Все права защищены.
    // Этот программный код является собственностью владельца.
    // Запрещается копирование, изменение, распространение или использование без явного разрешения.
    // Reset ready state when session changes
    setIsReady(false);
  }, []);

  return (
    <BuildContext.Provider
      value={{
        sessionId,
        isReady,
        setSessionId: handleSetSessionId,
        setIsReady,
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

