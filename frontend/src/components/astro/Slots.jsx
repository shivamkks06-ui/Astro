import { useState } from "react";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Loading, ErrorState, Empty, StatusPill } from "../States";
import { useApi } from "../../lib/useApi";
import { api, errMsg, fmtDate } from "../../lib/api";

export function Slots({ durations }) {
  const { data, loading, error, reload } = useApi("/astrologer/slots");
  const [start, setStart] = useState("");
  const [dur, setDur] = useState(30);
  const add = async (e) => {
    e.preventDefault();
    if (!start) return toast.error("Pick a start time");
    try { await api.post("/astrologer/slots", { start_at: new Date(start).toISOString(), duration_min: Number(dur) }); toast.success("Slot added"); reload(); } catch (e2) { toast.error(errMsg(e2)); }
  };
  const del = async (id) => { try { await api.delete(`/astrologer/slots/${id}`); reload(); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <div className="grid lg:grid-cols-[1fr_1.5fr] gap-8">
      <form onSubmit={add} className="rounded-2xl border p-6 space-y-4 bg-card/60 h-fit">
        <h3 className="text-lg">Add an availability slot</h3>
        <Input data-testid="slot-start" type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} className="bg-background" />
        <select data-testid="slot-duration" value={dur} onChange={(e) => setDur(e.target.value)} className="w-full h-10 rounded-md border bg-background px-3 text-sm">
          {durations.map((d) => <option key={d} value={d}>{d} minutes</option>)}
        </select>
        <Button data-testid="slot-add-button">Add slot</Button>
        <p className="text-xs text-muted-foreground">Times use your device's time zone. Slots must start at least 30 minutes from now and can't overlap.</p>
      </form>
      <div className="space-y-2">
        {loading ? <Loading /> : error ? <ErrorState error={error} onRetry={reload} /> : data.length === 0 ? <Empty title="No slots yet" hint="Add slots so customers can book you." /> :
          data.map((s) => (
            <div key={s.id} data-testid={`my-slot-${s.id}`} className="flex justify-between items-center rounded-xl border p-3 text-sm">
              <span>{fmtDate(s.start_at)} · {s.duration_min} min</span>
              <span className="flex items-center gap-2"><StatusPill status={s.status} />{s.status === "open" && <Button size="icon" variant="ghost" data-testid={`slot-delete-${s.id}`} onClick={() => del(s.id)}><Trash2 className="h-4 w-4" /></Button>}</span>
            </div>
          ))}
      </div>
    </div>
  );
}
