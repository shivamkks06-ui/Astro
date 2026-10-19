import { toast } from "sonner";
import { Button } from "../ui/button";
import { ActionDialog } from "../ActionDialog";
import { Loading, ErrorState, StatusPill } from "../States";
import { useApi } from "../../lib/useApi";
import { api, inr, fmtDate, label } from "../../lib/api";

const STATS = [["upcoming_paise", "Upcoming (confirmed bookings)"], ["on_hold_paise", "On hold (dispute window / unreconciled)"], ["eligible_paise", "Eligible"], ["requestable_paise", "Available to request"], ["processing_paise", "Payout processing"], ["paid_paise", "Paid out"]];

export function Earnings() {
  const { data, loading, error, reload } = useApi("/astrologer/earnings");
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const b = data.balances;
  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        {STATS.map(([k, l]) => (
          <div key={k} className="rounded-xl border p-4 bg-card/60" data-testid={`earn-${k}`}>
            <p className="text-[11px] text-muted-foreground leading-tight">{l}</p><p className="text-xl font-serif text-amber-200 mt-2">{inr(b[k])}</p>
          </div>
        ))}
      </div>
      <div className="flex flex-col sm:flex-row gap-4 sm:items-center justify-between rounded-xl border p-4">
        <p className="text-xs text-muted-foreground">Platform commission: {data.policy.commission_bps / 100}%. Earnings become eligible {data.policy.payout_hold_hours}h after a session ends, once the payment is reconciled and there's no open dispute. Minimum payout {inr(data.policy.min_payout_paise)}. Our team reviews every payout.</p>
        <ActionDialog testid="request-payout" trigger={<Button disabled={b.requestable_paise <= 0}>Request payout</Button>} title="Request a payout"
          description={`Up to ${inr(b.requestable_paise)}. Enter the amount in rupees.`} fields={[{ name: "amount", label: "Amount (₹)", type: "number" }]}
          onSubmit={async (v) => { await api.post("/astrologer/payouts", { amount_paise: Math.round(Number(v.amount || 0) * 100) }); reload(); toast.message("Payout request submitted for review"); }} />
      </div>
      <div>
        <h3 className="text-lg mb-3">Payouts</h3>
        {data.payouts.length === 0 ? <p className="text-sm text-muted-foreground">No payouts yet.</p> : data.payouts.map((p) => (
          <div key={p.id} data-testid={`payout-${p.id}`} className="flex flex-col sm:flex-row justify-between rounded-xl border p-3 mb-2 text-sm gap-2">
            <span>{fmtDate(p.created_at)} · {inr(p.amount_paise)}{p.settlement_ref ? ` · UTR ${p.settlement_ref} on ${fmtDate(p.settled_at)}` : ""}{p.failure_reason ? ` · ${label(p.failure_reason)}` : ""}{p.rejected_reason ? ` · ${p.rejected_reason}` : ""}</span>
            <StatusPill status={p.status} />
          </div>
        ))}
      </div>
      <div>
        <h3 className="text-lg mb-3">Earnings ledger</h3>
        <div className="overflow-x-auto rounded-xl border">
          <table className="w-full text-sm" data-testid="earnings-ledger">
            <thead className="text-left text-muted-foreground"><tr><th className="p-3">Date</th><th className="p-3">Type</th><th className="p-3">Credit</th><th className="p-3">Debit</th><th className="p-3">Available from</th></tr></thead>
            <tbody>
              {data.entries.length === 0 && <tr><td colSpan={5} className="p-6 text-center text-muted-foreground">No entries yet</td></tr>}
              {data.entries.map((e) => (
                <tr key={e.id} className="border-t"><td className="p-3">{fmtDate(e.created_at)}</td><td className="p-3 capitalize">{label(e.kind)}</td><td className="p-3 text-emerald-300">{e.credit ? inr(e.credit) : ""}</td><td className="p-3 text-red-300">{e.debit ? inr(e.debit) : ""}</td><td className="p-3">{e.available_at ? fmtDate(e.available_at) : "—"}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
