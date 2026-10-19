import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { FlaskConical } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Loading, ErrorState, StatusPill } from "../components/States";
import { useApi } from "../lib/useApi";
import { api, errMsg, inr } from "../lib/api";

export default function PayPage() {
  const { id } = useParams();
  const { data: p, loading, error, reload } = useApi(`/payments/${id}`);
  const [busy, setBusy] = useState(false);
  if (loading) return <Loading />;
  if (error) return <div className="max-w-lg mx-auto px-4 py-16"><ErrorState error={error} onRetry={reload} /></div>;
  const back = p.purpose === "listing" ? "/studio" : `/bookings/${p.booking_id}`;
  const run = async (outcome) => {
    setBusy(true);
    try {
      const { data } = await api.post(`/payments/${id}/mock-checkout`, { outcome });
      toast[data.status === "captured" ? "success" : "error"](`Payment ${data.status}. The server checked the signed webhook.`);
      reload();
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <div className="max-w-lg mx-auto px-4 py-16">
      <div className="glass rounded-2xl p-8 space-y-6">
        {p.provider_test_mode && (
          <div data-testid="mock-payment-banner" className="rounded-lg border border-sky-500/40 bg-sky-500/10 p-3 text-xs text-sky-200 flex gap-2">
            <FlaskConical className="h-4 w-4 shrink-0" />TEST MODE (MOCKED payment simulator). No real money moves. A real gateway such as Razorpay connects at this same point.
          </div>
        )}
        <h1 className="text-2xl">Checkout</h1>
        <div className="flex justify-between"><span className="text-muted-foreground capitalize">{p.purpose} payment</span><b data-testid="payment-amount" className="text-amber-300">{inr(p.amount_paise)}</b></div>
        <div className="flex justify-between text-sm"><span className="text-muted-foreground">Status</span><StatusPill status={p.status} testid="payment-status" /></div>
        <p className="text-xs text-muted-foreground">Order ref: <span className="font-mono">{p.provider_order_id}</span></p>
        {["created", "failed"].includes(p.status) && p.status !== "failed" ? (
          <div className="grid grid-cols-2 gap-3">
            <Button data-testid="mock-pay-success" disabled={busy} onClick={() => run("success")}>Simulate success</Button>
            <Button data-testid="mock-pay-failure" disabled={busy} variant="outline" onClick={() => run("failure")}>Simulate failure</Button>
          </div>
        ) : p.status === "failed" ? (
          <p className="text-sm text-red-300">Payment failed. Go back and try again; a new attempt will be created.</p>
        ) : null}
        <Button asChild variant="ghost" className="w-full"><Link data-testid="payment-back-link" to={back}>Back</Link></Button>
      </div>
    </div>
  );
}
