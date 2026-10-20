import { useEffect, useRef, useState } from "react";
import { MapPin, Globe, Loader2 } from "lucide-react";
import { Input } from "../ui/input";
import { Button } from "../ui/button";
import { api, errMsg } from "../../lib/api";
import { useLang } from "../../lib/i18n";

export function PlaceSearch({ value, onChange }) {
  const { t } = useLang();
  const [q, setQ] = useState(value?.label || "");
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const ticket = useRef(0);

  const search = async (online) => {
    const t = ++ticket.current;
    setBusy(true); setErr("");
    try {
      const { data } = await api.get("/places", { params: { q: q.trim(), online } });
      if (t === ticket.current) { setItems(data.items); setOpen(true); }
    } catch (e) {
      if (t === ticket.current) setErr(errMsg(e));
    } finally {
      if (t === ticket.current) setBusy(false);
    }
  };

  useEffect(() => {
    if (q.trim().length < 2 || q === value?.label) { setItems([]); return undefined; }
    const id = setTimeout(() => search(false), 250);
    return () => clearTimeout(id);
  }, [q]); // eslint-disable-line react-hooks/exhaustive-deps

  const pick = (p) => { onChange(p); setQ(p.label); setOpen(false); };
  return (
    <div className="relative">
      <div className="relative">
        <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input id="birth-place" data-testid="kundli-place-input" value={q} autoComplete="off" placeholder={t("Start typing a city, e.g. Varanasi")}
          className="pl-9 h-12" onChange={(e) => { setQ(e.target.value); if (value) onChange(null); }} onFocus={() => items.length && setOpen(true)} />
        {busy && <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-amber-300" />}
      </div>
      {value && <p data-testid="kundli-place-selected" className="mt-1.5 text-xs text-muted-foreground">{value.lat}, {value.lon} · {value.tz}</p>}
      {err && <p role="alert" className="mt-1.5 text-xs text-red-300">{err}</p>}
      {open && !value && q.trim().length >= 2 && (
        <div data-testid="kundli-place-results" className="absolute z-30 mt-1 w-full rounded-xl border bg-popover shadow-xl overflow-hidden">
          {items.map((p, i) => (
            <button type="button" key={`${p.lat}${p.lon}${i}`} data-testid={`kundli-place-option-${i}`} onClick={() => pick(p)}
              className="block w-full text-left px-3 py-2.5 min-h-11 text-sm hover:bg-amber-500/10 focus:bg-amber-500/10 border-b border-border/60 last:border-0">
              {p.label}<span className="block text-[11px] text-muted-foreground">{p.tz}{p.source === "openstreetmap" ? " · OpenStreetMap" : ""}</span>
            </button>
          ))}
          {!items.length && !busy && <p className="px-3 py-3 text-sm text-muted-foreground">{t("No city in the offline list.")}</p>}
          <Button type="button" variant="ghost" data-testid="kundli-place-online" disabled={busy || q.trim().length < 3} onClick={() => search(true)} className="w-full h-11 rounded-none text-amber-200">
            <Globe className="h-4 w-4 mr-2" />{t("Search worldwide (OpenStreetMap)")}
          </Button>
        </div>
      )}
    </div>
  );
}
