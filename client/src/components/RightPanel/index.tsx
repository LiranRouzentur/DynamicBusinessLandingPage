/**
 * Right Panel Container
 * Ref: Product.md > Section 1, line 43
 */

import SiteFrame from "./SiteFrame";

interface RightPanelProps {
  sessionId: string | null;
  isReady: boolean;
}

function RightPanel({ sessionId, isReady }: RightPanelProps) {
  return (
    <div className="h-full w-full bg-gray-100">
      <SiteFrame sessionId={sessionId} isReady={isReady} />
    </div>
  );
}

export default RightPanel;
