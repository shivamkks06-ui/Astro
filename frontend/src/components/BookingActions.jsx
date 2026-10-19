import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "./ui/button";
import { ActionDialog } from "./ActionDialog";
import { api, errMsg, idem, inr } from "../lib/api";

export function BookingActions({ b, reload }) {
  const nav = useNavigate();
  const key = useRef(idem());
  const role = b.viewer_role;
  const act = (action, reason = "") => api.post(`/bookings/${b.id}/actions/${action}`, { reason }).then(reload);
  const quick = async (action) => { try { await act(action); toast.success("Updated"); } catch (e) { toast.error(errMsg(e)); } };
  const pay = async () => {
    try {
      const { data } = await api.post(`/bookings/${b.id}/pay`, {}, { headers: { "Idempotency-Key": key.current } });
      nav(`/pay/${data.payment_id}`);
    } catch (e) { toast.error(errMsg(e)); }
  };
  const s = b.status;
  const cancelText = s === "confirmed" && role === "customer"
    ? `More than ${b.price.policy.cancellation_window_hours}h before the start: full refund. Later: ${b.price.policy.late_cancel_refund_pct}% refund.`
    : "This cannot be undone.";

  return (
    <div className="flex flex-wrap gap-3" data-testid="booking-actions">
      {role === "astrologer" && s === "requested" && <>
        <Button data-testid="action-accept" onClick={() => quick("accept")}>Accept request</Button>
        <ActionDialog testid="action-decline" trigger={<Button variant="outline">Decline</Button>} title="Decline this request?" fields={[{ name: "reason", label: "Reason (optional)" }]} onSubmit={(v) => act("decline", v.reason)} />
      </>}
      {role === "customer" && ["accepted", "payment_pending"].includes(s) && <Button data-testid="action-pay" onClick={pay}>Pay {inr(b.price.gross_paise)}</Button>}
      {role === "astrologer" && s === "confirmed" && <Button data-testid="action-start" onClick={() => quick("start")}>Start session</Button>}
      {s === "in_progress" && (
        <ActionDialog testid="action-complete" trigger={<Button variant="outline">End session</Button>} title="End this session now?"
          description={role === "astrologer" ? "If you end before the booked time, the customer gets a pro-rata refund for the unused minutes." : "If you leave early, unused minutes are not refunded."}
          onSubmit={() => act("complete")} />
      )}
      {role === "customer" && s === "confirmed" && (
        <ActionDialog testid="action-no-show" trigger={<Button variant="outline">Astrologer didn't show up</Button>} title="Report a no-show?"
          description="Available from 10 minutes after the scheduled start if the session hasn't begun. You get a full refund." onSubmit={() => act("claim_no_show")} />
      )}
      {["requested", "accepted", "payment_pending", "confirmed"].includes(s) && (
        <ActionDialog testid="action-cancel" trigger={<Button variant="ghost" className="text-red-300">Cancel booking</Button>} title="Cancel this booking?" description={cancelText} destructive
          fields={[{ name: "reason", label: "Reason (optional)" }]} onSubmit={(v) => act("cancel", v.reason)} />
      )}
      {role === "customer" && s === "completed" && !b.dispute_resolution && (
        <ActionDialog testid="action-dispute" trigger={<Button variant="ghost">Raise a dispute</Button>} title="Raise a dispute"
          description={`Within ${b.price.policy.dispute_window_hours}h of completion. The astrologer's earnings are held until we review it.`}
          fields={[{ name: "reason", label: "Describe the issue", type: "textarea" }]} onSubmit={(v) => act("dispute", v.reason || "")} />
      )}
    </div>
  );
}

export function Extensions({ b, reload }) {
  const nav = useNavigate();
  const key = useRef(idem());
  const role = b.viewer_role;
  const run = async (fn) => { try { await fn(); reload(); } catch (e) { toast.error(errMsg(e)); } };
  if (b.status !== "in_progress") return null;
  const pending = b.extensions_pending[0];
  return (
    <div className="rounded-xl border p-4 space-y-3" data-testid="extensions-panel">
      <p className="text-sm font-medium">Extend session</p>
      {!pending && role === "customer" && (
        <div className="flex gap-2 flex-wrap">
          {[5, 10, 15].map((m) => (
            <Button key={m} size="sm" variant="outline" data-testid={`extend-${m}`} onClick={() => run(() => api.post(`/bookings/${b.id}/extensions`, { minutes: m }))}>
              +{m} min · {inr(b.price.rate_paise_per_min * m)}
            </Button>
          ))}
        </div>
      )}
      {!pending && role === "astrologer" && <p className="text-xs text-muted-foreground">The customer can ask for more time. You'll be asked to agree first.</p>}
      {pending?.status === "pending_consent" && (role === "astrologer" ? (
        <div className="flex gap-2 items-center flex-wrap">
          <span className="text-sm">Customer asks for +{pending.minutes} min</span>
          <Button size="sm" data-testid="extension-accept" onClick={() => run(() => api.post(`/bookings/${b.id}/extensions/${pending.id}/respond`, { accept: true }))}>Agree</Button>
          <Button size="sm" variant="ghost" data-testid="extension-decline" onClick={() => run(() => api.post(`/bookings/${b.id}/extensions/${pending.id}/respond`, { accept: false }))}>Decline</Button>
        </div>
      ) : <p className="text-xs text-muted-foreground">Waiting for the astrologer to agree to +{pending.minutes} min.</p>)}
      {pending?.status === "awaiting_payment" && role === "customer" && (
        <Button size="sm" data-testid="extension-pay" onClick={() => run(async () => {
          const { data } = await api.post(`/bookings/${b.id}/extensions/${pending.id}/pay`, {}, { headers: { "Idempotency-Key": key.current } });
          nav(`/pay/${data.payment_id}`);
        })}>Pay {inr(pending.amount_paise)} for +{pending.minutes} min</Button>
      )}
    </div>
  );
}
