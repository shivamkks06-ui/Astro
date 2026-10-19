import { useState } from "react";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Loading, ErrorState, Empty } from "../States";
import { useApi } from "../../lib/useApi";
import { api, errMsg } from "../../lib/api";

const BLANK = { label: "Self", full_name: "", birth_date: "", birth_time: "", birth_place: "" };

export function BirthProfiles() {
  const { data, loading, error, reload } = useApi("/me/birth-profiles");
  const [f, setF] = useState(BLANK);
  const [busy, setBusy] = useState(false);
  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/me/birth-profiles", { ...f, birth_time: f.birth_time || null });
      toast.success("Birth profile saved");
      setF(BLANK);
      reload();
    } catch (e2) { toast.error(errMsg(e2)); } finally { setBusy(false); }
  };
  const del = async (id) => { try { await api.delete(`/me/birth-profiles/${id}`); reload(); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <div className="grid lg:grid-cols-2 gap-8">
      <form onSubmit={save} className="rounded-2xl border p-6 space-y-4 bg-card/60" data-testid="birth-profile-form">
        <h3 className="text-lg">Add a birth profile</h3>
        {[["label", "Label (e.g. Self, Mother)", "text"], ["full_name", "Full name", "text"], ["birth_date", "Date of birth", "date"], ["birth_time", "Time of birth (optional)", "time"], ["birth_place", "Place of birth", "text"]].map(([k, l, t]) => (
          <div key={k} className="space-y-1.5"><Label>{l}</Label><Input data-testid={`birth-${k}`} type={t} required={k !== "birth_time"} value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} className="bg-background" /></div>
        ))}
        <Button data-testid="birth-save-button" disabled={busy}>Save profile</Button>
      </form>
      <div className="space-y-3">
        {loading ? <Loading /> : error ? <ErrorState error={error} onRetry={reload} /> : data.length === 0 ? <Empty title="No birth profiles" hint="Saved profiles can be shared with an astrologer when you book." /> :
          data.map((p) => (
            <div key={p.id} data-testid={`birth-profile-${p.id}`} className="rounded-xl border p-4 flex justify-between items-start bg-card/60">
              <div><p className="font-medium">{p.label}: {p.full_name}</p><p className="text-xs text-muted-foreground">{p.birth_date} {p.birth_time || ""} · {p.birth_place}</p></div>
              <Button size="icon" variant="ghost" data-testid={`birth-delete-${p.id}`} onClick={() => del(p.id)}><Trash2 className="h-4 w-4" /></Button>
            </div>
          ))}
      </div>
    </div>
  );
}
