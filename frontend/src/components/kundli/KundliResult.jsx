import { useState } from "react";
import { Calculator, RotateCcw } from "lucide-react";
import { NorthChart, SouthChart } from "./Charts";
import { DashaPanel } from "./DashaPanel";

const deg = (d) => `${Math.floor(d)}°${String(Math.floor((d % 1) * 60)).padStart(2, "0")}′`;

function Summary({ chart }) {
  const items = [["Ascendant (Lagna)", `${chart.ascendant.sign} ${deg(chart.ascendant.degree)}`], ["Moon sign (Rashi)", `${chart.moon_sign} · ${chart.moon_rashi}`],
    ["Janma nakshatra", `${chart.janma_nakshatra}, pada ${chart.janma_pada}`], ["Current dasha", chart.dasha.current ? `${chart.dasha.current.mahadasha} / ${chart.dasha.current.antardasha}` : "—"]];
  return (
    <dl className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {items.map(([k, v]) => (
        <div key={k} className="rounded-xl border bg-card/60 p-3"><dt className="text-[11px] uppercase tracking-wider text-muted-foreground">{k}</dt><dd data-testid={`kundli-summary-${k.split(" ")[0].toLowerCase()}`} className="mt-1 text-sm font-semibold text-amber-100">{v}</dd></div>
      ))}
    </dl>
  );
}

function PlanetTable({ chart }) {
  return (
    <div className="overflow-x-auto rounded-xl border">
      <table data-testid="kundli-planet-table" className="w-full min-w-[520px] text-sm">
        <thead className="bg-secondary/60 text-left text-xs uppercase tracking-wider text-muted-foreground">
          <tr>{["Planet", "Sign", "Degree", "House", "Nakshatra", "Pada"].map((h) => <th key={h} className="px-3 py-2.5 font-medium">{h}</th>)}</tr>
        </thead>
        <tbody>
          {[{ ...chart.ascendant, name: "Ascendant", house: 1 }, ...chart.planets].map((p) => (
            <tr key={p.name} className="border-t border-border/60">
              <td className="px-3 py-2.5 font-medium">{p.name}{p.retrograde && !["Rahu", "Ketu"].includes(p.name) && <span title="Retrograde" className="ml-1 text-xs text-amber-300">(R)</span>}</td>
              <td className="px-3 py-2.5">{p.sign}</td><td className="px-3 py-2.5 font-mono text-xs">{deg(p.degree)}</td><td className="px-3 py-2.5">{p.house}</td>
              <td className="px-3 py-2.5">{p.nakshatra}</td><td className="px-3 py-2.5">{p.pada}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function KundliResult({ input, chart, style, onStyle, actions, onEdit }) {
  const [s, setS] = useState(style || "north");
  const pick = (v) => { setS(v); onStyle?.(v); };
  const b = chart.birth;
  return (
    <section data-testid="kundli-result" className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="overline mb-1 flex items-center gap-1.5"><Calculator className="h-3.5 w-3.5" />Calculated chart</p>
          <h2 className="text-2xl">{input.name || "Birth chart"}</h2>
          <p className="text-sm text-muted-foreground">{input.date} · {input.time} · {input.place} (UTC{b.utc_offset_hours >= 0 ? "+" : ""}{b.utc_offset_hours})</p>
        </div>
        <div className="flex gap-2">{onEdit && <button type="button" data-testid="kundli-edit" onClick={onEdit} className="inline-flex items-center gap-1.5 min-h-11 px-3 text-sm text-amber-200"><RotateCcw className="h-4 w-4" />New chart</button>}{actions}</div>
      </div>
      <Summary chart={chart} />
      <div className="grid lg:grid-cols-[380px_1fr] gap-6 items-start">
        <div className="space-y-3">
          <div role="tablist" aria-label="Chart style" className="grid grid-cols-2 rounded-full border p-1">
            {[["north", "North Indian"], ["south", "South Indian"]].map(([v, l]) => (
              <button key={v} role="tab" type="button" aria-selected={s === v} data-testid={`chart-style-${v}`} onClick={() => pick(v)}
                className={`min-h-10 rounded-full text-sm transition-colors ${s === v ? "bg-primary text-primary-foreground font-semibold" : "text-muted-foreground"}`}>{l}</button>
            ))}
          </div>
          {s === "north" ? <NorthChart chart={chart} /> : <SouthChart chart={chart} />}
          <p className="text-[11px] text-muted-foreground text-center">Numbers in the North chart are sign numbers (1 = Aries). (R) = retrograde.</p>
        </div>
        <div className="space-y-6 min-w-0"><PlanetTable chart={chart} /><DashaPanel dasha={chart.dasha} /></div>
      </div>
      <p data-testid="kundli-method" className="text-xs text-muted-foreground">Method: {chart.system.zodiac} zodiac, {chart.system.ayanamsa} ayanamsa ({chart.system.ayanamsa_degrees.toFixed(2)}°), {chart.system.houses} houses, {chart.system.nodes}, {chart.system.ephemeris} ephemeris. These are astronomical calculations; any reading of them is interpretive guidance, not a prediction.</p>
    </section>
  );
}
