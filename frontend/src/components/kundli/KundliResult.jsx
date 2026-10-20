import { useState } from "react";
import { Calculator, RotateCcw } from "lucide-react";
import { NorthChart, SouthChart } from "./Charts";
import { DashaPanel } from "./DashaPanel";
import { PanchangCard, ManglikCard, ShareBar } from "./KundliExtras";
import { useLang } from "../../lib/i18n";

const deg = (d) => `${Math.floor(d)}°${String(Math.floor((d % 1) * 60)).padStart(2, "0")}′`;

function Summary({ chart }) {
  const { t, lang } = useLang();
  const items = [["Ascendant (Lagna)", `${t(chart.ascendant.sign)} ${deg(chart.ascendant.degree)}`], ["Moon sign (Rashi)", lang === "hi" ? t(chart.moon_sign) : `${chart.moon_sign} · ${chart.moon_rashi}`],
    ["Janma nakshatra", `${t(chart.janma_nakshatra)}, ${t("pada")} ${chart.janma_pada}`], ["Current dasha", chart.dasha.current ? `${t(chart.dasha.current.mahadasha)} / ${t(chart.dasha.current.antardasha)}` : "—"]];
  return (
    <dl className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {items.map(([k, v]) => (
        <div key={k} className="rounded-xl border bg-card/60 p-3"><dt className="text-[11px] uppercase tracking-wider text-muted-foreground">{t(k)}</dt><dd data-testid={`kundli-summary-${k.split(" ")[0].toLowerCase()}`} className="mt-1 text-sm font-semibold text-amber-100">{v}</dd></div>
      ))}
    </dl>
  );
}

function PlanetTable({ chart }) {
  const { t } = useLang();
  return (
    <div className="overflow-x-auto rounded-xl border">
      <table data-testid="kundli-planet-table" className="w-full min-w-[520px] text-sm">
        <thead className="bg-secondary/60 text-left text-xs uppercase tracking-wider text-muted-foreground">
          <tr>{["Planet", "Sign", "Degree", "House", "Nakshatra", "Pada"].map((h) => <th key={h} className="px-3 py-2.5 font-medium">{t(h)}</th>)}</tr>
        </thead>
        <tbody>
          {[{ ...chart.ascendant, name: "Ascendant", house: 1 }, ...chart.planets].map((p) => (
            <tr key={p.name} className="border-t border-border/60">
              <td className="px-3 py-2.5 font-medium">{t(p.name)}{p.retrograde && !["Rahu", "Ketu"].includes(p.name) && <span title="Retrograde" className="ml-1 text-xs text-amber-300">{t("(R)")}</span>}</td>
              <td className="px-3 py-2.5">{t(p.sign)}</td><td className="px-3 py-2.5 font-mono text-xs">{deg(p.degree)}</td><td className="px-3 py-2.5">{p.house}</td>
              <td className="px-3 py-2.5">{t(p.nakshatra)}</td><td className="px-3 py-2.5">{p.pada}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function KundliResult({ input, chart, style, onStyle, actions, onEdit }) {
  const [s, setS] = useState(style || "north");
  const [div, setDiv] = useState("d1");
  const view = div === "d1" ? chart : chart.navamsa;
  const pick = (v) => { setS(v); onStyle?.(v); };
  const b = chart.birth;
  const { t } = useLang();
  return (
    <section data-testid="kundli-result" className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="overline mb-1 flex items-center gap-1.5"><Calculator className="h-3.5 w-3.5" />{t("Calculated chart")}</p>
          <h2 className="text-2xl">{input.name || t("Birth chart")}</h2>
          <p className="text-sm text-muted-foreground">{input.date} · {input.time} · {input.place} (UTC{b.utc_offset_hours >= 0 ? "+" : ""}{b.utc_offset_hours})</p>
        </div>
        <div className="flex flex-wrap gap-2 print:hidden">{onEdit && <button type="button" data-testid="kundli-edit" onClick={onEdit} className="inline-flex items-center gap-1.5 min-h-11 px-3 text-sm text-amber-200"><RotateCcw className="h-4 w-4" />{t("New chart")}</button>}{actions}<ShareBar input={input} chart={chart} /></div>
      </div>
      <Summary chart={chart} />
      <div className="grid lg:grid-cols-[380px_1fr] gap-6 items-start">
        <div className="space-y-3">
          <div role="tablist" aria-label="Divisional chart" className="grid grid-cols-2 rounded-full border p-1 print:hidden">
            {[["d1", "Rashi (D1)"], ["d9", "Navamsa (D9)"]].map(([v, l]) => (
              <button key={v} role="tab" type="button" aria-selected={div === v} data-testid={`chart-div-${v}`} onClick={() => setDiv(v)}
                className={`min-h-10 rounded-full text-sm transition-colors ${div === v ? "bg-amber-400/20 text-amber-100 font-semibold" : "text-muted-foreground"}`}>{t(l)}</button>
            ))}
          </div>
          <div role="tablist" aria-label="Chart style" className="grid grid-cols-2 rounded-full border p-1 print:hidden">
            {[["north", "North Indian"], ["south", "South Indian"]].map(([v, l]) => (
              <button key={v} role="tab" type="button" aria-selected={s === v} data-testid={`chart-style-${v}`} onClick={() => pick(v)}
                className={`min-h-10 rounded-full text-sm transition-colors ${s === v ? "bg-primary text-primary-foreground font-semibold" : "text-muted-foreground"}`}>{t(l)}</button>
            ))}
          </div>
          {s === "north" ? <NorthChart chart={view} testid={div === "d1" ? "chart-north" : "chart-north-d9"} /> : <SouthChart chart={view} label={div === "d1" ? "RASHI" : "NAVAMSA"} />}
          <p className="text-[11px] text-muted-foreground text-center">{t(s === "north" ? "Numbers are sign numbers (1 = Aries); house 1 is the top diamond." : "Signs are fixed; Asc marks the Lagna.")} {t("(R) = retrograde.")}{div === "d9" && ` ${t("The table below shows Rashi (D1) positions.")}`}</p>
        </div>
        <div className="space-y-6 min-w-0"><PlanetTable chart={chart} /><div className="grid sm:grid-cols-2 gap-4"><PanchangCard p={chart.panchang} /><ManglikCard m={chart.manglik} /></div><DashaPanel dasha={chart.dasha} /></div>
      </div>
      <p data-testid="kundli-method" className="text-xs text-muted-foreground">{t("Method")}: {chart.system.zodiac} zodiac, {chart.system.ayanamsa} ayanamsa ({chart.system.ayanamsa_degrees.toFixed(2)}°), {chart.system.houses} houses, {chart.system.nodes}, {chart.system.ephemeris} ephemeris. {t("These are astronomical calculations; any reading of them is interpretive guidance, not a prediction.")}</p>
    </section>
  );
}
