import { Capacitor } from "@capacitor/core";
import { Printer, Share2, AlertTriangle, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../ui/button";

export function PanchangCard({ p }) {
  const rows = [["Tithi", `${p.paksha} ${p.tithi}`], ["Vara", p.vara], ["Nakshatra", p.nakshatra], ["Yoga", p.yoga], ["Karana", p.karana], ["Sunrise", p.sunrise || "—"]];
  return (
    <div data-testid="kundli-panchang" className="rounded-xl border p-4 space-y-3">
      <h3 className="text-lg">Panchang at birth</h3>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        {rows.map(([k, v]) => <div key={k}><dt className="text-[11px] uppercase tracking-wider text-muted-foreground">{k}</dt><dd className="font-medium">{v}</dd></div>)}
      </dl>
      <p className="text-[11px] text-muted-foreground">{p.note}</p>
    </div>
  );
}

export function ManglikCard({ m }) {
  const cancelled = m.manglik && m.cancellations.length > 0;
  const Icon = m.manglik && !cancelled ? AlertTriangle : CheckCircle2;
  const status = !m.manglik ? "Not Manglik" : cancelled ? "Manglik, traditionally cancelled" : "Manglik";
  return (
    <div data-testid="kundli-manglik" className="rounded-xl border p-4 space-y-2">
      <h3 className="text-lg">Manglik check</h3>
      <p data-testid="kundli-manglik-status" className={`inline-flex items-center gap-1.5 text-sm font-semibold ${m.manglik && !cancelled ? "text-orange-300" : "text-emerald-300"}`}><Icon className="h-4 w-4" />{status}</p>
      <p className="text-sm text-muted-foreground">Mars is in house {m.mars_house_from_lagna} from the Lagna ({m.from_lagna ? "counts" : "does not count"}) and house {m.mars_house_from_moon} from the Moon ({m.from_moon ? "counts" : "does not count"}).</p>
      {cancelled && <p className="text-sm text-muted-foreground">Cancellation: {m.cancellations.join("; ")}.</p>}
      <p className="text-[11px] text-muted-foreground">{m.rule} Manglik status is a traditional indicator only. It does not decide whether a marriage will work.</p>
    </div>
  );
}

export const summaryText = (input, c) => [
  `NakshatraVeda Kundli${input.name ? `: ${input.name}` : ""}`,
  `${input.date} ${input.time}, ${input.place}`,
  `Lagna: ${c.ascendant.sign} · Moon: ${c.moon_sign} (${c.moon_rashi}) · Nakshatra: ${c.janma_nakshatra} pada ${c.janma_pada}`,
  `Navamsa Lagna: ${c.navamsa.ascendant.sign}`,
  `Panchang: ${c.panchang.paksha} ${c.panchang.tithi}, ${c.panchang.vara}, ${c.panchang.yoga} yoga`,
  c.dasha.current ? `Dasha now: ${c.dasha.current.mahadasha}/${c.dasha.current.antardasha} (until ${c.dasha.current.until})` : "",
  ...c.planets.map((p) => `${p.name}: ${p.sign} ${p.degree.toFixed(2)}°, house ${p.house}, ${p.nakshatra}`),
].filter(Boolean).join("\n");

export function ShareBar({ input, chart }) {
  const share = async () => {
    const text = summaryText(input, chart);
    try {
      if (navigator.share) { await navigator.share({ title: "My Kundli", text }); return; }
      await navigator.clipboard.writeText(text);
      toast.success("Kundli summary copied. Paste it into WhatsApp or any app.");
    } catch (e) {
      if (e?.name !== "AbortError") toast.error("Could not share. Please try again.");
    }
  };
  return (
    <div className="flex gap-2 print:hidden">
      <Button type="button" variant="outline" data-testid="kundli-share" onClick={share} className="rounded-full h-11"><Share2 className="h-4 w-4 mr-2" />Share</Button>
      {!Capacitor.isNativePlatform() && <Button type="button" variant="outline" data-testid="kundli-print" onClick={() => window.print()} className="rounded-full h-11"><Printer className="h-4 w-4 mr-2" />Print / PDF</Button>}
    </div>
  );
}
