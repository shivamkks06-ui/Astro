import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { ActionDialog } from "../ActionDialog";
import { StatusPill } from "../States";
import { api, errMsg, idem, inr, fmtDate } from "../../lib/api";

export function Listing({ data, plans, reload }) {
  const nav = useNavigate();
  const key = useRef(idem());
  const p = data.profile;
  const buy = async (plan) => {
    try {
      const { data: r } = await api.post("/astrologer/subscriptions", { plan_id: plan.id }, { headers: { "Idempotency-Key": `${key.current}-${plan.id}` } });
      nav(`/pay/${r.payment_id}`);
    } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div className="space-y-8">
      <div className="rounded-xl border p-4 text-sm" data-testid="listing-expiry">
        {p.listing_expires_at && new Date(p.listing_expires_at) > new Date() ? <>Listing active until <b className="text-amber-300">{fmtDate(p.listing_expires_at)}</b>. Buying again extends it from that date.</> : "No active listing. Customers can't find or book you until you have one."}
      </div>
      {p.identity_status !== "approved" && <p className="text-sm text-amber-200" data-testid="listing-requires-kyc">Your identity verification has to be approved before you can buy a listing.</p>}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        {plans.map((pl) => (
          <div key={pl.id} className="glass gold-border rounded-2xl p-6 space-y-3" data-testid={`plan-${pl.code}`}>
            <p className="overline">{pl.code}</p>
            <h3 className="text-2xl">{pl.name}</h3>
            <p className="text-3xl font-serif text-amber-300">{inr(pl.price_paise)}</p>
            <p className="text-sm text-muted-foreground">{pl.duration_days} days of public listing</p>
            <Button data-testid={`buy-plan-${pl.code}`} className="w-full rounded-full" disabled={p.identity_status !== "approved"} onClick={() => buy(pl)}>Buy listing</Button>
          </div>
        ))}
      </div>
      <div>
        <h3 className="text-lg mb-3">Subscription history</h3>
        {data.subscriptions.length === 0 ? <p className="text-sm text-muted-foreground">No subscriptions yet.</p> : data.subscriptions.map((s) => (
          <div key={s.id} data-testid={`subscription-${s.id}`} className="rounded-xl border p-3 mb-2 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-sm">
            <span>{s.plan.name} · {inr(s.plan.price_paise)} · {s.activated_at ? `${fmtDate(s.activated_at)} → ${fmtDate(s.expires_at)}` : "awaiting payment"}{s.payment_ref ? ` · ref ${s.payment_ref}` : ""}{s.cancel_requested ? " · won't renew" : ""}</span>
            <span className="flex items-center gap-2"><StatusPill status={s.status} />
              {s.status === "active" && !s.cancel_requested && (
                <ActionDialog testid={`cancel-sub-${s.id}`} trigger={<Button size="sm" variant="ghost">Cancel</Button>} title="Stop this subscription?" description="Your listing stays active until it expires. Refunds are handled by our team on request."
                  onSubmit={() => api.post(`/astrologer/subscriptions/${s.id}/cancel`).then(reload)} />
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
