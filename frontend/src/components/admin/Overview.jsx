import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Loading, ErrorState, StatusPill } from "../States";
import { ActionDialog } from "../ActionDialog";
import { useApi } from "../../lib/useApi";
import { api, inr, label } from "../../lib/api";

export function Overview() {
  const o = useApi("/admin/overview");
  const fin = useApi("/admin/finance/summary");
  if (o.loading || fin.loading) return <Loading />;
  if (o.error || fin.error) return <ErrorState error={o.error || fin.error} onRetry={() => { o.reload(); fin.reload(); }} />;
  const stats = Object.entries(o.data).filter(([, v]) => typeof v === "number");
  return (
    <div className="space-y-8">
      <div className="flex flex-wrap gap-3 text-xs">
        <span data-testid="provider-status" className="rounded-full border px-3 py-1">Payments: {o.data.payment_provider.name} {o.data.payment_provider.test_mode && <b className="text-sky-300">(MOCKED, test mode)</b>}</span>
        <span data-testid="calls-status" className="rounded-full border px-3 py-1">Calls: {o.data.calls.provider} · <b className="text-amber-300">not operational</b></span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {stats.map(([k, v]) => <div key={k} data-testid={`stat-${k}`} className="rounded-xl border p-4 bg-card/60"><p className="text-[11px] text-muted-foreground capitalize">{label(k)}</p><p className="text-2xl font-serif mt-1">{v}</p></div>)}
      </div>
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="rounded-xl border p-4 overflow-x-auto">
          <div className="flex justify-between mb-3"><h3 className="text-lg">Ledger accounts</h3><StatusPill status={fin.data.trial_balance_ok ? "approved" : "failed"} testid="trial-balance" /></div>
          <table className="w-full text-xs"><thead className="text-muted-foreground text-left"><tr><th className="p-2">Account</th><th className="p-2">Debit</th><th className="p-2">Credit</th><th className="p-2">Net credit</th></tr></thead>
            <tbody>{fin.data.accounts.map((a) => <tr key={a.account} className="border-t"><td className="p-2 font-mono">{a.account}</td><td className="p-2">{inr(a.debit)}</td><td className="p-2">{inr(a.credit)}</td><td className="p-2">{inr(a.balance)}</td></tr>)}</tbody></table>
        </div>
        <div className="rounded-xl border p-4 overflow-x-auto">
          <h3 className="text-lg mb-3">Commission report</h3>
          <table className="w-full text-xs" data-testid="commission-report"><thead className="text-muted-foreground text-left"><tr><th className="p-2">Astrologer</th><th className="p-2">Sessions</th><th className="p-2">Gross</th><th className="p-2">Refunds</th><th className="p-2">Commission</th><th className="p-2">Share</th></tr></thead>
            <tbody>{fin.data.commission_report.map((r) => <tr key={r.astrologer_id} className="border-t"><td className="p-2">{r.name || r.astrologer_id.slice(0, 8)}</td><td className="p-2">{r.bookings}</td><td className="p-2">{inr(r.gross)}</td><td className="p-2">{inr(r.refunds)}</td><td className="p-2">{inr(r.commission)}</td><td className="p-2">{inr(r.share)}</td></tr>)}</tbody></table>
        </div>
      </div>
    </div>
  );
}

export function SettingsPanel() {
  const { data, loading, error, reload } = useApi("/admin/settings");
  const [vals, setVals] = useState({});
  useEffect(() => { if (data) setVals(data.settings); }, [data]);
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const changed = Object.fromEntries(Object.entries(vals).filter(([k, v]) => Number(v) !== data.settings[k]).map(([k, v]) => [k, Number(v)]));
  return (
    <div className="space-y-4 max-w-3xl">
      <div className="grid sm:grid-cols-2 gap-4">
        {Object.entries(data.limits).map(([k, [lo, hi]]) => (
          <label key={k} className="rounded-xl border p-3 text-sm space-y-1.5 block">
            <span className="capitalize">{label(k)}</span><span className="text-[11px] text-muted-foreground block">range {lo}–{hi}{k.endsWith("_bps") ? " (basis points; 2500 = 25%)" : k.endsWith("_paise") ? " (paise)" : ""}</span>
            <Input data-testid={`setting-${k}`} type="number" value={vals[k] ?? ""} onChange={(e) => setVals({ ...vals, [k]: e.target.value })} className="bg-background" />
          </label>
        ))}
      </div>
      <ActionDialog testid="settings-save" trigger={<Button disabled={!Object.keys(changed).length}>Save changes</Button>} title="Apply platform settings?"
        description={`Changes: ${JSON.stringify(changed)}. New bookings use them; existing bookings keep the price they were booked at.`}
        onSubmit={() => api.put("/admin/settings", changed).then(() => { reload(); toast.message("Settings audited and saved"); })} />
    </div>
  );
}
