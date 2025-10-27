/**
 * Main application component
 * Ref: Product.md > Section 1, lines 36-43
 *
 * Layout: Horizontal split (30/70)
 * - Left Panel: Search and progress log
 * - Right Panel: Generated landing page in iframe
 */

import { useState } from "react";
import LeftPanel from "./components/LeftPanel";
import RightPanel from "./components/RightPanel";

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Left Panel - 30% width */}
      <div className="w-[30%] flex flex-col border-r border-gray-200">
        <LeftPanel
          onSessionStart={setSessionId}
          sessionId={sessionId}
          onReady={setIsReady}
        />
      </div>

      {/* Right Panel - 70% width */}
      <div className="w-[70%]">
        <RightPanel sessionId={sessionId} isReady={isReady} />
      </div>
    </div>
  );
}

export default App;
