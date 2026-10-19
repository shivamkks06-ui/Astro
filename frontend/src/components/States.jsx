import { Loader2, AlertTriangle, Inbox, RotateCw } from "lucide-react";
import { Button } from "./ui/button";
import { label } from "../lib/api";

export const Loading = ({ text = "Loading" }) => (
  <div data-testid="loading-indicator" className="flex items-center gap-3 py-12 justify-center text-muted-foreground">
    <Loader2 className="h-5 w-5 animate-spin text-amber-400" /> {text}…
  </div>
);

export const ErrorState = ({ error, onRetry }) => (
  <div data-testid="error-state" className="glass rounded-xl p-6 flex flex-col sm:flex-row sm:items-center gap-4">
    <AlertTriangle className="h-6 w-6 text-red-400 shrink-0" />
    <p className="flex-1 text-sm">{error}</p>
    {onRetry && (
      <Button data-testid="retry-button" variant="outline" onClick={onRetry}><RotateCw className="h-4 w-4 mr-2" />Retry</Button>
    )}
  </div>
);

export const Empty = ({ title, hint, children }) => (
  <div data-testid="empty-state" className="rounded-xl border border-dashed p-10 text-center">
    <Inbox className="h-8 w-8 mx-auto text-amber-400/70 mb-3" />
    <p className="font-serif text-lg">{title}</p>
    {hint && <p className="text-sm text-muted-foreground mt-1">{hint}</p>}
    {children && <div className="mt-4">{children}</div>}
  </div>
);

const TONE = {
  approved: "emerald", active: "emerald", completed: "emerald", confirmed: "emerald", captured: "emerald", paid: "emerald", processed: "emerald", resolved: "emerald", actioned: "emerald",
  submitted: "amber", requested: "amber", accepted: "amber", payment_pending: "amber", pending: "amber", pending_payment: "amber", processing: "amber", in_progress: "sky", open: "amber", created: "amber", approved_payout: "amber",
  rejected: "red", cancelled: "red", failed: "red", expired: "slate", disputed: "red", suspended: "red", refunded: "slate", duplicate: "red", amount_mismatch: "red", deleted: "slate",
};
const CLS = {
  emerald: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  amber: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  sky: "bg-sky-500/10 text-sky-300 border-sky-500/30",
  red: "bg-red-500/10 text-red-300 border-red-500/30",
  slate: "bg-slate-500/10 text-slate-300 border-slate-500/30",
};
export const StatusPill = ({ status, testid }) => (
  <span data-testid={testid || `status-${status}`} className={`inline-flex items-center px-2.5 py-0.5 rounded-full border text-xs font-medium capitalize ${CLS[TONE[status] || "slate"]}`}>
    {label(String(status))}
  </span>
);
