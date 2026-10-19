import { useState } from "react";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { Switch } from "../ui/switch";
import { ActionDialog } from "../ActionDialog";
import { Loading, Empty, StatusPill } from "../States";
import { useApi } from "../../lib/useApi";
import { api, errMsg, fmtDate } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";

export function Blocks() {
  const { data, loading, reload } = useApi("/me/blocks");
  if (loading) return <Loading />;
  if (!data?.length) return <Empty title="You haven't blocked anyone" hint="Use Block on a profile or booking page to stop all contact." />;
  return data.map((b) => (
    <div key={b.user_id} className="flex justify-between items-center rounded-xl border p-3 mb-2">
      <span>{b.name}</span>
      <Button size="sm" variant="outline" data-testid={`unblock-${b.user_id}`} onClick={() => api.delete(`/me/blocks/${b.user_id}`).then(reload)}>Unblock</Button>
    </div>
  ));
}

export function Privacy() {
  const { user, refreshMe } = useAuth();
  const del = useApi("/me/deletion-request");
  const [pv, setPv] = useState({ share_birth_details: user.privacy?.share_birth_details ?? true, marketing_opt_in: user.privacy?.marketing_opt_in ?? false });
  const save = async (next) => {
    setPv(next);
    try { await api.put("/me/privacy", next); toast.success("Privacy settings saved"); refreshMe(); } catch (e) { toast.error(errMsg(e)); }
  };
  const exportData = async () => {
    try {
      const { data } = await api.get("/me/export");
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      a.download = "my-nakshatraveda-data.json";
      a.click();
    } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div className="space-y-6 max-w-2xl">
      {user.role === "customer" && (
        <label className="flex items-center justify-between rounded-xl border p-4 gap-4">
          <span className="text-sm">Share my selected birth profile with the astrologer for confirmed bookings</span>
          <Switch data-testid="privacy-share-birth" checked={pv.share_birth_details} onCheckedChange={(v) => save({ ...pv, share_birth_details: v })} />
        </label>
      )}
      <label className="flex items-center justify-between rounded-xl border p-4 gap-4">
        <span className="text-sm">Send me product updates by email</span>
        <Switch data-testid="privacy-marketing" checked={pv.marketing_opt_in} onCheckedChange={(v) => save({ ...pv, marketing_opt_in: v })} />
      </label>
      <div className="rounded-xl border p-4 flex justify-between items-center gap-4">
        <span className="text-sm">Download a copy of your data (JSON)</span>
        <Button variant="outline" data-testid="export-data-button" onClick={exportData}>Export</Button>
      </div>
      <div className="rounded-xl border border-red-500/30 p-4 space-y-3">
        <p className="text-sm">Account deletion. We review each request and then anonymise your account. Financial records are kept as the law requires.</p>
        {del.data ? <p className="text-sm" data-testid="deletion-status">Request {fmtDate(del.data.created_at)}: <StatusPill status={del.data.status} /></p> : null}
        {(!del.data || del.data.status !== "pending") && (
          <ActionDialog testid="request-deletion" destructive trigger={<Button variant="destructive">Request deletion</Button>} title="Request account deletion?"
            description="Any active bookings must finish first." fields={[{ name: "reason", label: "Reason (optional)", type: "textarea" }]}
            onSubmit={(v) => api.post("/me/deletion-request", { reason: v.reason || "" }).then(del.reload)} />
        )}
      </div>
    </div>
  );
}
