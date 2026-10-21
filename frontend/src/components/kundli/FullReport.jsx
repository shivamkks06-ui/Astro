import { useState } from "react";
import { ChevronDown, Calculator, BookOpen, Sparkles, Clock, Loader2, Lock } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { api, errMsg } from "../../lib/api";
import { useLang } from "../../lib/i18n";

// flip to true once real payments exist; premium sections then show a lock
const PREMIUM_LOCK = false;
const AI_FOR = { overview: "personality", career: "career", finance: "finance", relationships: "relationships", education: "education", family: "wellbeing", dasha: "dasha" };

function Items({ items }) {
  return (
    <div className="grid sm:grid-cols-2 gap-3">
      {items.map((it) => (
        <div key={it.title} className="rounded-xl border border-border/70 bg-secondary/30 p-3">
          <p className="font-semibold text-amber-100 text-sm mb-1.5">{it.title}</p>
          <dl className="space-y-1 text-xs">{it.rows.map(([k, v]) => <div key={k}><dt className="inline text-muted-foreground">{k}: </dt><dd className="inline break-words">{String(v)}</dd></div>)}</dl>
        </div>
      ))}
    </div>
  );
}

function Section({ s, ai, open, onToggle }) {
  const { t } = useLang();
  const locked = PREMIUM_LOCK && s.premium;
  return (
    <div data-testid={`report-section-${s.id}`} className="rounded-2xl border border-amber-400/20 bg-card/60">
      <button type="button" aria-expanded={open} onClick={onToggle} data-testid={`report-toggle-${s.id}`}
        className="w-full flex items-center gap-3 px-4 sm:px-5 min-h-14 text-left">
        <span className="flex-1 font-serif text-base sm:text-lg text-amber-100">{t(s.title)}</span>
        {s.time_sensitive && <span className="inline-flex items-center gap-1 rounded-full border border-orange-400/40 px-2 py-0.5 text-[10px] text-orange-200"><Clock className="h-3 w-3" />{t("Depends on birth time")}</span>}
        {locked && <Lock className="h-4 w-4 text-amber-300" />}
        <ChevronDown className={`h-4 w-4 shrink-0 text-amber-300 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (locked ? <p className="px-5 pb-5 text-sm text-muted-foreground">{t("Premium, coming soon")}</p> : (
        <div className="px-4 sm:px-5 pb-5 space-y-4">
          {s.facts.length > 0 && <div className="space-y-1.5"><p className="inline-flex items-center gap-1 text-[11px] uppercase tracking-wider text-muted-foreground"><Calculator className="h-3 w-3" />{t("Calculated")}</p>
            <ul className="space-y-1 text-sm">{s.facts.map((f) => <li key={f} className="break-words">{f}</li>)}</ul></div>}
          {s.text.length > 0 && <div className="space-y-1.5"><p className="inline-flex items-center gap-1 text-[11px] uppercase tracking-wider text-amber-300/90"><BookOpen className="h-3 w-3" />{t("Traditional interpretation")}</p>
            {s.text.map((x) => <p key={x} className="text-sm text-slate-300 leading-relaxed">{x}</p>)}</div>}
          {ai && <div data-testid={`report-ai-${s.id}`} className="space-y-1.5 rounded-xl border border-amber-400/25 bg-amber-400/5 p-3"><p className="inline-flex items-center gap-1 text-[11px] uppercase tracking-wider text-amber-300"><Sparkles className="h-3 w-3" />{t("AI interpretation")}</p><p className="text-sm leading-relaxed">{ai}</p></div>}
          {s.items.length > 0 && <Items items={s.items} />}
          {s.unavailable.length > 0 && <p className="text-xs text-muted-foreground">{t("Not available")}: {s.unavailable.join(", ")}.</p>}
        </div>
      ))}
    </div>
  );
}

function AiBar({ savedId, ai, setAi }) {
  const { t } = useLang();
  const [busy, setBusy] = useState(false);
  if (ai) return null;
  if (!savedId) return <p data-testid="report-ai-hint" className="text-xs text-muted-foreground">{t("Save this chart to request an optional AI interpretation written from these calculations.")}</p>;
  const run = async () => {
    if (busy) return;
    setBusy(true);
    try { const { data } = await api.post(`/kundlis/${savedId}/ai-report`, {}, { timeout: 120000 }); setAi(data); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <Button type="button" variant="outline" data-testid="report-ai-button" onClick={run} disabled={busy} className="rounded-full h-11 border-amber-400/40">
      {busy ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}{t(busy ? "Writing AI interpretation (up to a minute)" : "Get AI interpretation")}
    </Button>
  );
}

export function FullReport({ report, savedId, aiReport }) {
  const { t } = useLang();
  const [full, setFull] = useState(false);
  const [open, setOpen] = useState({ overview: true });
  const [ai, setAi] = useState(aiReport || null);
  const all = full ? report.sections : report.sections.slice(0, 1);
  return (
    <section data-testid="kundli-report" className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><p className="overline mb-1">{t("Detailed Kundli report")}</p><h3 className="text-2xl">{t("Your full report")}</h3></div>
        <AiBar savedId={savedId} ai={ai} setAi={setAi} />
      </div>
      {report.time_unknown && <p data-testid="report-time-warning" className="rounded-xl border border-orange-400/40 bg-orange-400/10 p-3 text-sm text-orange-100">{t("Birth time is unknown, so the chart uses 12:00 noon. Sections marked 'Depends on birth time' may be inaccurate.")}</p>}
      <div className="space-y-3">
        {all.map((s) => <Section key={s.id} s={s} ai={ai?.sections?.[AI_FOR[s.id]]} open={!!open[s.id]} onToggle={() => setOpen({ ...open, [s.id]: !open[s.id] })} />)}
      </div>
      <Button type="button" data-testid="report-read-full" onClick={() => setFull(!full)} className="w-full sm:w-auto rounded-full h-12 px-8 font-semibold">
        {t(full ? "Show summary only" : "Read full report")}
      </Button>
    </section>
  );
}
