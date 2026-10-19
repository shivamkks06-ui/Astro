import { toast } from "sonner";
import { Button } from "../ui/button";
import { Loading, ErrorState, Empty, StatusPill } from "../States";
import { useApi } from "../../lib/useApi";
import { api, errMsg, inr, fmtDate, label } from "../../lib/api";

async function downloadReceipt(id) {
  try {
    const { data } = await api.get(`/me/payments/${id}/receipt`);
    const lines = [`NakshatraVeda Receipt ${data.receipt_no}`, `Issued to: ${data.issued_to} <${data.email}>`, `Purpose: ${data.purpose}`, `Amount: ${inr(data.amount_paise)} INR`,
      `Paid at: ${fmtDate(data.paid_at)}`, `Provider: ${data.provider} (${data.provider_payment_id})`, `Refunded: ${inr(data.refunded_paise)}`, data.note];
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/plain" }));
    a.download = `${data.receipt_no}.txt`;
    a.click();
  } catch (e) { toast.error(errMsg(e)); }
}

export function Payments() {
  const { data, loading, error, reload } = useApi("/me/payments");
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return (
    <div className="space-y-8">
      {data.payments.length === 0 ? <Empty title="No payments yet" /> : (
        <div className="overflow-x-auto rounded-xl border">
          <table className="w-full text-sm" data-testid="payments-table">
            <thead className="text-left text-muted-foreground"><tr><th className="p-3">Date</th><th className="p-3">Purpose</th><th className="p-3">Amount</th><th className="p-3">Status</th><th className="p-3"></th></tr></thead>
            <tbody>{data.payments.map((p) => (
              <tr key={p.id} className="border-t">
                <td className="p-3">{fmtDate(p.created_at)}</td><td className="p-3 capitalize">{p.purpose}</td><td className="p-3">{inr(p.amount_paise)}</td><td className="p-3"><StatusPill status={p.status} /></td>
                <td className="p-3">{["captured", "duplicate"].includes(p.status) && <Button size="sm" variant="ghost" data-testid={`receipt-${p.id}`} onClick={() => downloadReceipt(p.id)}>Receipt</Button>}</td>
              </tr>))}
            </tbody>
          </table>
        </div>
      )}
      <div>
        <h3 className="text-lg mb-3">Refunds</h3>
        {data.refunds.length === 0 ? <p className="text-sm text-muted-foreground">No refunds.</p> : data.refunds.map((r) => (
          <div key={r.id} data-testid={`refund-${r.id}`} className="flex justify-between rounded-xl border p-3 mb-2 text-sm"><span>{label(r.reason)} · {fmtDate(r.created_at)}</span><span>{inr(r.amount_paise)} <StatusPill status={r.status} /></span></div>
        ))}
      </div>
    </div>
  );
}
