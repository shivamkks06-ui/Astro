import { ActionDialog } from "./ActionDialog";
import { api } from "../lib/api";

const REASONS = ["harassment", "coercion_or_pressure", "guaranteed_outcome_claims", "fraud", "inappropriate_content", "spam", "other"];

export function ReportBlock({ targetId, bookingId, trigger, mode }) {
  if (mode === "block") {
    return (
      <ActionDialog testid="block-user" trigger={trigger} title="Block this user?" destructive confirmLabel="Block"
        description="You won't be able to book or message each other. You can unblock from your account's Safety tab."
        onSubmit={() => api.post("/me/blocks", { user_id: targetId })} />
    );
  }
  return (
    <ActionDialog testid="report-user" trigger={trigger} title="Report a concern"
      description="Pressure to buy more sessions, fear-based claims and guaranteed predictions are all reportable. Our safety team reviews every report."
      fields={[{ name: "reason", label: "Reason", type: "select", options: REASONS }, { name: "details", label: "What happened?", type: "textarea" }]}
      onSubmit={(v) => api.post("/reports", { target_user_id: targetId, booking_id: bookingId || null, reason: v.reason || "other", details: v.details || "" })} />
  );
}
