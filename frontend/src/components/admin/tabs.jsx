import { Link } from "react-router-dom";
import { Button } from "../ui/button";
import { ActionDialog } from "../ActionDialog";
import { StatusPill } from "../States";
import { VerificationReview } from "./VerificationReview";
import { api, inr, fmtDate, label } from "../../lib/api";

const st = (k = "status") => ({ label: label(k), render: (r) => <StatusPill status={String(r[k])} /> });
const dt = (k = "created_at", l = "Created") => ({ label: l, render: (r) => fmtDate(r[k]) });
const money = (k, l) => ({ label: l, render: (r) => inr(k.split(".").reduce((o, p) => o?.[p], r)) });
const id = (k = "id", l = "ID") => ({ label: l, render: (r) => <span className="font-mono">{String(r[k] || "—").slice(0, 10)}</span> });
const reasonField = [{ name: "reason", label: "Reason (recorded in audit log)", type: "textarea" }];
const A = (testid, text, title, fields, fn, destructive) => (
  <ActionDialog key={testid} testid={testid} destructive={destructive} trigger={<Button size="sm" variant={destructive ? "destructive" : "outline"}>{text}</Button>} title={title} fields={fields} onSubmit={fn} />
);

export const ADMIN_TABS = [
  { v: "users", l: "Users", cols: [id(), { label: "Name", key: "name" }, { label: "Email", key: "email" }, { label: "Role", key: "role" }, st(), dt()],
    actions: (r, reload) => r.role !== "admin" && r.status !== "deleted" && (r.status === "active"
      ? A(`suspend-${r.id}`, "Suspend", `Suspend ${r.email}?`, reasonField, (v) => api.post(`/admin/users/${r.id}/status`, { status: "suspended", reason: v.reason || "" }).then(reload), true)
      : A(`activate-${r.id}`, "Reactivate", `Reactivate ${r.email}?`, reasonField, (v) => api.post(`/admin/users/${r.id}/status`, { status: "active", reason: v.reason || "" }).then(reload))) },
  { v: "verification_cases", l: "Verification", cols: [id("astrologer_id", "Astrologer"), { label: "Kind", key: "kind" }, st(), dt("submitted_at", "Submitted"), { label: "Notes", key: "review_notes" }],
    actions: (r, reload) => <VerificationReview id={r.id} onDone={reload} /> },
  { v: "astrologer_profiles", l: "Astrologers", cols: [id(), { label: "Name", key: "display_name" }, st("identity_status"), st("credential_status"), dt("listing_expires_at", "Listing expires"), st("account_status")] },
  { v: "listing_plans", l: "Plans", cols: [{ label: "Code", key: "code" }, { label: "Name", key: "name" }, money("price_paise", "Price"), { label: "Days", key: "duration_days" }, st("active")],
    actions: (r, reload) => A(`edit-plan-${r.code}`, "Edit", `Edit ${r.name}`, [{ name: "price", label: "Price (₹)", type: "number" }, { name: "duration_days", label: "Duration (days)", type: "number" }, { name: "active", label: "Active", type: "select", options: ["true", "false"] }],
      (v) => api.patch(`/admin/plans/${r.id}`, { ...(v.price ? { price_paise: Math.round(Number(v.price) * 100) } : {}), ...(v.duration_days ? { duration_days: Number(v.duration_days) } : {}), ...(v.active ? { active: v.active === "true" } : {}) }).then(reload)) },
  { v: "listing_subscriptions", l: "Subscriptions", cols: [id(), id("astrologer_id", "Astrologer"), { label: "Plan", render: (r) => r.plan?.name }, money("plan.price_paise", "Price"), st(), dt("expires_at", "Expires"), { label: "Payment ref", key: "payment_ref" }, { label: "Refund", key: "refund_status" }],
    actions: (r, reload) => ["active", "cancelled"].includes(r.status) && A(`refund-sub-${r.id}`, "Refund", "Refund this listing in full?", reasonField, (v) => api.post(`/admin/subscriptions/${r.id}/refund`, { reason: v.reason || "" }).then(reload), true) },
  { v: "bookings", l: "Bookings", cols: [id(), { label: "Mode", key: "mode" }, st(), dt("slot_start", "Slot"), money("price.gross_paise", "Price"), { label: "Settlement", render: (r) => (r.settlement ? `refund ${inr(r.settlement.refund)} / charged ${inr(r.settlement.retained)}` : "—") }],
    actions: (r, reload) => [<Button key="v" asChild size="sm" variant="ghost"><Link to={`/bookings/${r.id}`} data-testid={`view-booking-${r.id}`}>View</Link></Button>,
      ["requested", "accepted", "payment_pending", "confirmed"].includes(r.status) && A(`admin-cancel-${r.id}`, "Cancel", "Cancel the booking with a full refund?", reasonField, (v) => api.post(`/admin/bookings/${r.id}/cancel`, { reason: v.reason || "" }).then(reload), true)] },
  { v: "payments", l: "Payments", cols: [id(), { label: "Purpose", key: "purpose" }, money("amount_paise", "Amount"), money("gateway_fee_paise", "Fee"), st(), st("reconciled"), { label: "Provider ref", key: "provider_payment_id" }, dt()],
    actions: (r, reload) => r.status === "captured" && !r.reconciled && A(`reconcile-${r.id}`, "Reconcile", "Check this payment against the provider's record?", [], () => api.post(`/admin/payments/${r.id}/reconcile`).then(reload)) },
  { v: "ledger_entries", l: "Ledger", cols: [dt(), { label: "Journal", key: "journal_id" }, { label: "Kind", key: "kind" }, { label: "Account", key: "account" }, money("debit", "Debit"), money("credit", "Credit")] },
  { v: "payouts", l: "Payouts", cols: [id(), id("astrologer_id", "Astrologer"), money("amount_paise", "Amount"), st(), { label: "Account", render: (r) => `${r.payout_account?.beneficiary_name} · ${r.payout_account?.upi_id || `xx${r.payout_account?.account_last4}`}` }, { label: "UTR", key: "settlement_ref" }, dt()],
    actions: (r, reload) => r.status === "requested" ? [A(`approve-payout-${r.id}`, "Approve", `Approve payout of ${inr(r.amount_paise)}?`, [], () => api.post(`/admin/payouts/${r.id}/approve`).then(reload)),
      A(`reject-payout-${r.id}`, "Reject", "Reject this payout?", reasonField, (v) => api.post(`/admin/payouts/${r.id}/reject`, { reason: v.reason || "" }).then(reload), true)]
      : r.status === "processing" ? [A(`settle-ok-${r.id}`, "Mock: settled", "Simulate the provider confirming settlement (MOCKED)", [], () => api.post(`/admin/payouts/${r.id}/mock-settlement`, { outcome: "processed" }).then(reload)),
        A(`settle-fail-${r.id}`, "Mock: failed", "Simulate the provider reporting a failure (MOCKED)", [], () => api.post(`/admin/payouts/${r.id}/mock-settlement`, { outcome: "failed" }).then(reload), true)] : null },
  { v: "refunds_disputes", l: "Refunds & disputes", cols: [{ label: "Type", key: "type" }, id("booking_id", "Booking"), money("amount_paise", "Amount"), { label: "Reason", key: "reason" }, st(), dt()],
    actions: (r, reload) => r.type === "dispute" && r.status === "open" && A(`resolve-dispute-${r.booking_id}`, "Resolve", "Resolve this dispute", [{ name: "refund", label: "Refund to customer (₹, 0 for none)", type: "number" }, { name: "notes", label: "Resolution notes", type: "textarea" }],
      (v) => api.post(`/admin/disputes/${r.booking_id}/resolve`, { refund_paise: Math.round(Number(v.refund || 0) * 100), notes: v.notes || "" }).then(reload), true) },
  { v: "reports", l: "Reports", cols: [{ label: "Reason", key: "reason" }, id("target_user_id", "Target"), { label: "Details", key: "details" }, st(), dt()],
    actions: (r, reload) => r.status === "open" && A(`resolve-report-${r.id}`, "Resolve", "Resolve this report", [{ name: "status", label: "Outcome", type: "select", options: ["actioned", "dismissed"] }, { name: "notes", label: "Notes", type: "textarea" }, { name: "suspend_user", label: "Suspend the reported user", type: "checkbox" }],
      (v) => api.post(`/admin/reports/${r.id}/resolve`, { status: v.status || "dismissed", notes: v.notes || "", suspend_user: !!v.suspend_user }).then(reload)) },
  { v: "reviews", l: "Reviews", cols: [{ label: "Rating", key: "rating" }, { label: "Comment", key: "comment" }, st("hidden"), dt()],
    actions: (r, reload) => A(`moderate-${r.id}`, r.hidden ? "Unhide" : "Hide", r.hidden ? "Show this review again?" : "Hide this review?", reasonField, (v) => api.post(`/admin/reviews/${r.id}/moderate`, { hidden: !r.hidden, reason: v.reason || "" }).then(reload)) },
  { v: "deletion_requests", l: "Deletions", cols: [{ label: "Email", key: "email" }, { label: "Role", key: "role" }, { label: "Reason", key: "reason" }, st(), dt()],
    actions: (r, reload) => r.status === "pending" && [A(`approve-del-${r.id}`, "Anonymise", "Anonymise this account? This can't be undone.", [{ name: "notes", label: "Notes", type: "textarea" }], (v) => api.post(`/admin/deletion-requests/${r.id}/process`, { approve: true, notes: v.notes || "" }).then(reload), true),
      A(`reject-del-${r.id}`, "Reject", "Reject this deletion request?", [{ name: "notes", label: "Notes", type: "textarea" }], (v) => api.post(`/admin/deletion-requests/${r.id}/process`, { approve: false, notes: v.notes || "" }).then(reload))] },
  { v: "call_sessions", l: "Calls", cols: [id("booking_id", "Booking"), { label: "Provider", key: "provider" }, st(), dt()] },
  { v: "webhook_events", l: "Webhooks", cols: [id(), { label: "Type", key: "type" }, st(), dt("received_at", "Received")] },
  { v: "audit_logs", l: "Audit log", cols: [dt("created_at", "When"), { label: "Actor", render: (r) => `${r.actor_role} ${String(r.actor_id).slice(0, 8)}` }, { label: "Action", key: "action" }, { label: "Target", render: (r) => `${r.target_type}:${String(r.target_id || "").slice(0, 10)}` }, { label: "Details", render: (r) => <span className="font-mono text-[10px]">{JSON.stringify(r.details).slice(0, 160)}</span> }] },
];
