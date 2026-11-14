import { useState } from "react";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Loading, ErrorState, Empty, StatusPill } from "../States";
import { useApi } from "../../lib/useApi";
import { api, errMsg, fmtDate } from "../../lib/api";

const TIMES = Array.from({ length: 48 }, (_, i) => `${String(Math.floor(i / 2)).padStart(2, "0")}:${i % 2 ? "30" : "00"}`);
const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };

function OnlineToggle() {
  const { data, reload } = useApi("/astrologer/online");
  const on = !!data?.online;
  const flip = async () => { try { await api.post("/astrologer/online", { online: !on }); toast.success(on ? "You are offline" : "You are online for 3 hours"); reload(); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <button type="button" data-testid="astro-online-toggle" onClick={flip} className={`w-full flex items-center justify-between rounded-2xl border p-4 min-h-14 ${on ? "border-emerald-400/50 bg-emerald-500/10" : "bg-card/60"}`}>
      <span className="flex items-center gap-2 text-sm"><span className={`h-3 w-3 rounded-full ${on ? "bg-emerald-400 animate-pulse" : "bg-slate-500"}`} />{on ? "Online now: customers see you live" : "Offline: tap to go online"}</span>
      <span className={`relative h-6 w-11 rounded-full ${on ? "bg-emerald-500" : "bg-slate-600"}`}><span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${on ? "translate-x-5" : "translate-x-0.5"}`} /></span>
    </button>
  );
}

export function Slots({ durations }) {
  const { data, loading, error, reload } = useApi("/astrologer/slots");
  const [day, setDay] = useState(today());
  const [time, setTime] = useState("");
  const [dur, setDur] = useState(30);
  const add = async (e) => {
    e.preventDefault();
    if (!day || !time) return toast.error("Pick a date and a start time");
    const [y, mo, d] = day.split("-").map(Number);
    const [h, mi] = time.split(":").map(Number);
    try { await api.post("/astrologer/slots", { start_at: new Date(y, mo - 1, d, h, mi).toISOString(), duration_min: Number(dur) }); toast.success("Slot added"); reload(); } catch (e2) { toast.error(errMsg(e2)); }
  };
  const del = async (id) => { try { await api.delete(`/astrologer/slots/${id}`); reload(); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.5fr] gap-8">
      <div className="space-y-4">
      <OnlineToggle />
      <form onSubmit={add} className="rounded-2xl border p-6 space-y-4 bg-card/60 h-fit">
        <h3 className="text-lg">Add an availability slot</h3>
        <label className="block text-xs text-muted-foreground">Date<Input data-testid="slot-date" type="date" min={today()} value={day} onChange={(e) => setDay(e.target.value)} className="bg-background mt-1 h-11" /></label>
        <label className="block text-xs text-muted-foreground">Start time
          <select data-testid="slot-time" value={time} onChange={(e) => setTime(e.target.value)} className="mt-1 w-full h-11 rounded-md border bg-background px-3 text-sm text-foreground">
            <option value="">Choose time</option>
            {TIMES.map((x) => <option key={x} value={x}>{x}</option>)}
          </select>
        </label>
        <select data-testid="slot-duration" value={dur} onChange={(e) => setDur(e.target.value)} className="w-full h-11 rounded-md border bg-background px-3 text-sm">
          {durations.map((d) => <option key={d} value={d}>{d} minutes</option>)}
        </select>
        <Button data-testid="slot-add-button">Add slot</Button>
        <p className="text-xs text-muted-foreground">Times use your device's time zone. Slots must start at least 30 minutes from now and can't overlap.</p>
      </form>
      </div>
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
