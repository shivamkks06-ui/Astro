import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { useLang } from "../../lib/i18n";

export function DashaPanel({ dasha }) {
  const { t, locale } = useLang();
  const fmt = (d) => new Date(d).toLocaleDateString(locale, { day: "numeric", month: "short", year: "numeric" });
  const [open, setOpen] = useState(false);
  const cur = dasha.mahadashas.find((m) => m.antardashas);
  return (
    <div data-testid="kundli-dasha" className="rounded-xl border p-4 space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-lg">{t("Vimshottari dasha")}</h3>
        <span className="text-xs text-muted-foreground">{t("Balance at birth")}: {dasha.balance_years_at_birth} {t("yrs")}</span>
      </div>
      {cur ? (
        <>
          <p className="text-sm">{t("Now running")} <strong className="text-amber-200">{t(cur.lord)} {t("mahadasha")}</strong> ({fmt(cur.start)} – {fmt(cur.end)})</p>
          <ol className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {cur.antardashas.map((a) => (
              <li key={a.lord + a.start} className={`rounded-lg px-3 py-2 text-xs border ${a.current ? "border-amber-400/60 bg-amber-400/10 text-amber-100" : "border-border/60 text-muted-foreground"}`}>
                <span className="font-semibold">{t(cur.lord)}–{t(a.lord)}</span>{a.current && <span className="ml-1">{t("(current)")}</span>}<span className="block">{fmt(a.start)} – {fmt(a.end)}</span>
              </li>
            ))}
          </ol>
        </>
      ) : <p className="text-sm text-muted-foreground">{t("No running period in the calculated 120-year cycle.")}</p>}
      <button type="button" data-testid="kundli-dasha-toggle" aria-expanded={open} onClick={() => setOpen(!open)} className="inline-flex items-center gap-1 min-h-11 text-sm text-amber-200">
        {t("All mahadashas")}<ChevronDown className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <ul className="divide-y divide-border/60 text-sm">
          {dasha.mahadashas.map((m) => <li key={m.lord + m.start} className="flex justify-between py-2"><span>{t(m.lord)} ({m.years} {t("yrs")})</span><span className="text-muted-foreground">{fmt(m.start)} – {fmt(m.end)}</span></li>)}
        </ul>
      )}
    </div>
  );
}
