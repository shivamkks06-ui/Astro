import { useEffect, useRef, useState } from "react";
import { MapPin, Globe, Loader2, PenLine } from "lucide-react";
import { Input } from "../ui/input";
import { Button } from "../ui/button";
import { api, errMsg } from "../../lib/api";
import { useLang } from "../../lib/i18n";

const ZONES = (() => { try { return Intl.supportedValuesOf("timeZone"); } catch { return ["Asia/Kolkata", "UTC"]; } })();

function ManualPlace({ initial, onDone, onCancel }) {
  const { t } = useLang();
  const [m, setM] = useState({ name: initial || "", lat: "", lon: "", tz: "Asia/Kolkata" });
  const [err, setErr] = useState("");
  const save = () => {
    const lat = Number(m.lat), lon = Number(m.lon);
    if (!m.name.trim()) return setErr(t("Enter the place name."));
    if (m.lat === "" || !(lat >= -66.5 && lat <= 66.5)) return setErr(t("Latitude must be between -66.5 and 66.5."));
    if (m.lon === "" || !(lon >= -180 && lon <= 180)) return setErr(t("Longitude must be between -180 and 180."));
    onDone({ label: `${m.name.trim()} (manual)`, name: m.name.trim(), lat: Math.round(lat * 10000) / 10000, lon: Math.round(lon * 10000) / 10000, tz: m.tz, source: "manual" });
  };
  const f = (k) => (e) => setM({ ...m, [k]: e.target.value });
  return (
    <div data-testid="place-manual" className="mt-2 rounded-xl border border-orange-300/40 p-3 space-y-2">
      <p className="text-xs text-orange-200">{t("Manual coordinates are not verified. Copy them from a trusted map; a small error can change the Lagna.")}</p>
      <Input data-testid="place-manual-name" placeholder={t("Place name")} value={m.name} onChange={f("name")} />
      <div className="grid grid-cols-2 gap-2">
        <Input data-testid="place-manual-lat" inputMode="decimal" placeholder={t("Latitude, e.g. 25.3176")} value={m.lat} onChange={f("lat")} />
        <Input data-testid="place-manual-lon" inputMode="decimal" placeholder={t("Longitude, e.g. 82.9739")} value={m.lon} onChange={f("lon")} />
      </div>
      <select data-testid="place-manual-tz" value={m.tz} onChange={f("tz")} aria-label={t("Time zone")} className="w-full h-12 rounded-md border border-input bg-[#0E1830] px-3 text-sm">
        {ZONES.map((z) => <option key={z} value={z}>{z}</option>)}
      </select>
      {err && <p role="alert" className="text-xs text-red-300">{err}</p>}
      <div className="flex gap-2"><Button type="button" data-testid="place-manual-save" onClick={save} className="rounded-full h-10">{t("Use these coordinates")}</Button>
        <Button type="button" variant="ghost" onClick={onCancel} className="h-10">{t("Cancel")}</Button></div>
    </div>
  );
}

export function PlaceSearch({ value, onChange }) {
  const { t } = useLang();
  const [q, setQ] = useState(value?.label || "");
  const [res, setRes] = useState({ items: [], has_more: false, page: 0 });
  const [open, setOpen] = useState(false);
  const [manual, setManual] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const ticket = useRef(0);

  const search = async (online, page = 0) => {
    const tk = ++ticket.current;
    setBusy(true); setErr("");
    try {
      const { data } = await api.get("/places", { params: { q: q.trim(), online, page } });
      if (tk === ticket.current) { setRes((r) => ({ ...data, items: page ? [...r.items, ...data.items] : data.items })); setOpen(true); }
    } catch (e) {
      if (tk === ticket.current) setErr(errMsg(e));
    } finally {
      if (tk === ticket.current) setBusy(false);
    }
  };

  useEffect(() => {
    if (q.trim().length < 2 || q === value?.label) { setRes({ items: [], has_more: false, page: 0 }); return undefined; }
    const id = setTimeout(() => search(false), 250);
    return () => clearTimeout(id);
  }, [q]); // eslint-disable-line react-hooks/exhaustive-deps

  const pick = (p) => { onChange(p); setQ(p.label); setOpen(false); setManual(false); };
  const items = res.items;
  return (
    <div className="relative">
      <div className="relative">
        <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input id="birth-place" data-testid="kundli-place-input" value={q} autoComplete="off" placeholder={t("City, state or country, e.g. Varanasi")}
          className="pl-9 h-12" onChange={(e) => { setQ(e.target.value); if (value) onChange(null); }} onFocus={() => items.length && setOpen(true)} />
        {busy && <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-amber-300" />}
      </div>
      {value && <p data-testid="kundli-place-selected" className="mt-1.5 text-xs text-muted-foreground">{value.lat}, {value.lon} · {value.tz}
        {value.source === "manual" && <span data-testid="kundli-place-unverified" className="ml-1 text-orange-200">· {t("unverified coordinates")}</span>}</p>}
      {err && <p role="alert" className="mt-1.5 text-xs text-red-300">{err}</p>}
      {manual && <ManualPlace initial={q.trim()} onDone={pick} onCancel={() => setManual(false)} />}
      {open && !value && !manual && q.trim().length >= 2 && (
        <div data-testid="kundli-place-results" className="absolute z-30 mt-1 w-full max-h-[60vh] overflow-y-auto rounded-xl border bg-popover shadow-xl">
          {items.map((p, i) => (
            <button type="button" key={`${p.geonames_id || p.lat + "," + p.lon}-${i}`} data-testid={`kundli-place-option-${i}`} onClick={() => pick(p)}
              className="block w-full text-left px-3 py-2.5 min-h-11 text-sm hover:bg-amber-500/10 focus:bg-amber-500/10 border-b border-border/60">
              {p.label}<span className="block text-[11px] text-muted-foreground">{p.district && p.district !== p.name ? `${p.district} district · ` : ""}{p.tz}{p.source === "openstreetmap" ? " · OpenStreetMap" : ""}</span>
            </button>
          ))}
          {!items.length && !busy && <p className="px-3 py-3 text-sm text-muted-foreground">{t("No matching place found.")}</p>}
          {res.has_more && <Button type="button" variant="ghost" data-testid="kundli-place-more" disabled={busy} onClick={() => search(false, res.page + 1)} className="w-full h-11 rounded-none text-amber-200">{t("Show more places")}</Button>}
          <Button type="button" variant="ghost" data-testid="kundli-place-online" disabled={busy || q.trim().length < 3} onClick={() => search(true)} className="w-full h-11 rounded-none text-amber-200">
            <Globe className="h-4 w-4 mr-2" />{t("Search worldwide (OpenStreetMap)")}
          </Button>
          <Button type="button" variant="ghost" data-testid="kundli-place-manual" onClick={() => { setManual(true); setOpen(false); }} className="w-full h-11 rounded-none text-amber-200">
            <PenLine className="h-4 w-4 mr-2" />{t("Enter coordinates manually")}
          </Button>
          <p className="px-3 py-2 text-[10px] text-muted-foreground">{res.attribution || "Place data © GeoNames (geonames.org), CC BY 4.0"}</p>
        </div>
      )}
    </div>
  );
}
