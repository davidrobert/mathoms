import type { DecisionStatus } from "@/lib/api";

import {
  DECISION_STATUS_BADGE_CLASS,
  DECISION_STATUS_LABEL,
} from "./decisionsCopy";

interface DecisionStatusBadgeProps {
  status: DecisionStatus;
}

export function DecisionStatusBadge({ status }: DecisionStatusBadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
        DECISION_STATUS_BADGE_CLASS[status],
      ].join(" ")}
    >
      {DECISION_STATUS_LABEL[status]}
    </span>
  );
}
