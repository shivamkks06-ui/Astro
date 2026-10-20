import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CheckCircle2, MinusCircle, AlertTriangle, Sparkles, Calculator, ChevronDown } from "lucide-react";
import { Loading, ErrorState } from "../components/States";
import { useApi } from "../lib/useApi";
import { useLang } from "../lib/i18n";
import { LangToggle } from "../components/LangToggle";

const SIGNS = [["Aries", "Mesha", "♈"], ["Taurus", "Vrishabha", "♉"], ["Gemini", "Mithuna", "♊"], ["Cancer", "Karka", "♋"], ["Leo", "Simha", "♌"], ["Virgo", "Kanya", "♍"],
  ["Libra", "Tula", "♎"], ["Scorpio", "Vrishchika", "♏"], ["Sagittarius", "Dhanu", "♐"], ["Capricorn", "Makara", "♑"], ["Aquarius", "Kumbha", "♒"], ["Pisces", "Meena", "♓"]];
const TONE = { favourable: [CheckCircle2, "text-emerald-300 border-emerald-400/40 bg-emerald-400/10", "Favourable"],
  mixed: [MinusCircle, "text-slate-200 border-slate-400/40 bg-slate-400/10", "Mixed"], "take care": [AlertTriangle, "text-orange-300 border-orange-400/40 bg-orange-400/10", "Take care"] };
const CATS = [["career", "Career"], ["relationships", "Relationships"], ["health", "Health"], ["finance", "Finance"]];
const KEY = "nv:moon-sign";

const Tone = ({ t: tone }) => { const { t } = useLang(); const [I, c, l] = TONE[tone]; return <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${c}`}><I className="h-3 w-3" />{t(l)}</span>; };
const AiLabel = ({ note }) => { const { t, lang } = useLang(); return <span className="inline-flex flex-wrap items-center gap-1 text-[11px] uppercase tracking-wider text-amber-300"><Sparkles className="h-3 w-3" />{t("AI interpretation")}{note && lang === "hi" && <span className="normal-case tracking-normal text-muted-foreground">· {t("AI interpretation is shown in English.")}</span>}</span>; };
const CalcLabel = () => { const { t } = useLang(); return <span className="inline-flex items-center gap-1 text-[11px] uppercase tracking-wider text-muted-foreground"><Calculator className="h-3 w-3" />{t("Calculated reading")}</span>; };
const basisT = (b, t) => { const m = b.match(/^(\w+) in house (\d+) from (\w+)$/); return m ? t("{p} in house {n} from {s}", { p: t(m[1]), n: m[2], s: t(m[3]) }) : b; };

function SignPicker({ value, onPick }) {
  const { t, lang } = useLang();
  const ref = useRef(null);
  useEffect(() => { ref.current?.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: "nearest", inline: "center" }); }, [value]);
  return (
    <div ref={ref} role="tablist" aria-label="Moon sign" className="-mx-5 px-5 flex gap-2 overflow-x-auto pb-2 snap-x sm:mx-0 sm:px-0 sm:grid sm:grid-cols-6 lg:grid-cols-12">
      {SIGNS.map(([s, r, g], i) => (
        <button key={s} role="tab" type="button" aria-selected={value === i} data-testid={`sign-${s.toLowerCase()}`} onClick={() => onPick(i)}
          className={`snap-start shrink-0 w-[88px] sm:w-auto [overflow-wrap:normal] rounded-xl border px-1.5 py-2.5 text-center transition-colors ${value === i ? "border-amber-400 bg-amber-400/15 text-amber-100" : "bg-card/60 text-muted-foreground hover:text-foreground"}`}>
          <span aria-hidden="true" className="block text-xl leading-none text-amber-300">{g}&#xFE0E;</span>
          <span className="block mt-1 text-xs font-medium">{t(s)}</span><span className="block text-[10px] opacity-80">{lang === "hi" ? s : r}</span>
        </button>
      ))}
    </div>
  );
}

function Category({ id, label, c, ai }) {
  const { t } = useLang();
  const [open, setOpen] = useState(false);
  return (
    <article data-testid={`horoscope-cat-${id}`} className="rounded-2xl border bg-card/60 p-4 sm:p-5 space-y-2.5">
      <div className="flex items-center justify-between gap-2"><h3 className="text-lg">{t(label)}</h3><Tone t={c.tone} /></div>
      {ai && <div className="space-y-1"><AiLabel /><p data-testid={`horoscope-ai-${id}`} className="text-sm leading-relaxed">{ai}</p></div>}
      <div className="space-y-1"><CalcLabel /><p className="text-sm text-muted-foreground leading-relaxed">{t(c.text)}</p></div>
      <button type="button" aria-expanded={open} onClick={() => setOpen(!open)} className="inline-flex items-center gap-1 min-h-10 text-xs text-amber-200">{t("Why")}<ChevronDown className={`h-3.5 w-3.5 ${open ? "rotate-180" : ""}`} /></button>
      {open && <ul className="text-xs text-muted-foreground list-disc pl-4">{c.basis.map((b) => <li key={b}>{basisT(b, t)}</li>)}</ul>}
    </article>
  );
}

function usePollWhilePending(h, date) {
  const tries = useRef(0);
  useEffect(() => { tries.current = 0; }, [date]);
  useEffect(() => {
    if (h.data?.ai_status !== "pending" || tries.current >= 8) return undefined;
    const id = setTimeout(() => { tries.current += 1; h.reload(); }, 7000);
    return () => clearTimeout(id);
  }, [h.data]); // eslint-disable-line react-hooks/exhaustive-deps
}

export default function Horoscope() {
  const { t, lang, locale } = useLang();
  const [sp, setSp] = useSearchParams();
  const fromUrl = SIGNS.findIndex(([s]) => s.toLowerCase() === sp.get("sign"));
  const sign = fromUrl >= 0 ? fromUrl : Number(localStorage.getItem(KEY) ?? 0);
  const day = sp.get("day") || "today";
  const date = (() => { const d = new Date(Date.now() + 330 * 60000); d.setUTCDate(d.getUTCDate() + (day === "yesterday" ? -1 : day === "tomorrow" ? 1 : 0)); return d.toISOString().slice(0, 10); })();
  const h = useApi(`/horoscope/daily?date=${date}`);
  usePollWhilePending(h, date);
  const pick = (i) => { localStorage.setItem(KEY, String(i)); setSp((p) => { p.set("sign", SIGNS[i][0].toLowerCase()); return p; }, { replace: true }); };
  const setDay = (d) => setSp((p) => { p.set("day", d); return p; }, { replace: true });
  const r = h.data?.date === date ? h.data.signs[sign] : null;
  const title = { yesterday: "Yesterday under the stars", today: "Today under the stars", tomorrow: "Tomorrow under the stars" }[day] || "Today under the stars";

  return (
    <div className="max-w-7xl mx-auto px-5 sm:px-8 py-8 sm:py-12 space-y-6">
      <header className="max-w-2xl">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-2"><p className="overline">{t("Daily horoscope")}</p><LangToggle /></div>
        <h1 className="text-[1.875rem] leading-tight sm:text-5xl">{t(title)}</h1>
        <p className="mt-3 text-sm sm:text-base text-muted-foreground">{t("Pick your Moon sign (Rashi). Readings come from the day's real sidereal planet positions.")}</p>
      </header>
      <SignPicker value={sign} onPick={pick} />
      <div role="tablist" aria-label="Day" className="inline-grid grid-cols-3 rounded-full border p-1">
        {["yesterday", "today", "tomorrow"].map((d) => (
          <button key={d} role="tab" type="button" aria-selected={day === d} data-testid={`horoscope-day-${d}`} onClick={() => setDay(d)}
            className={`min-h-10 px-4 rounded-full text-sm capitalize ${day === d ? "bg-primary text-primary-foreground font-semibold" : "text-muted-foreground"}`}>{t(d)}</button>
        ))}
      </div>
      {h.error ? <ErrorState error={h.error} onRetry={h.reload} /> : !r ? <Loading text="Reading the transits" /> : (
        <div className="space-y-5">
          <section data-testid="horoscope-overview" className="glass rounded-2xl p-5 sm:p-7 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-2xl">{t(r.sign)} <span className="text-base text-muted-foreground">· {lang === "hi" ? r.sign : r.rashi}</span></h2>
              <div className="flex items-center gap-2"><span data-testid="horoscope-date" className="text-xs text-muted-foreground">{new Date(`${h.data.date}T12:00:00`).toLocaleDateString(locale, { weekday: "long", day: "numeric", month: "long" })}</span><Tone t={r.tone} /></div>
            </div>
            {r.ai ? <div className="space-y-1"><AiLabel note /><p data-testid="horoscope-ai-overview" className="leading-relaxed">{r.ai.overview}</p></div>
              : <p data-testid="horoscope-ai-status" className="text-xs text-muted-foreground">{t(h.data.ai_status === "pending" ? "AI interpretation is being written. The calculated reading is shown meanwhile." : "AI interpretation is unavailable right now; showing the calculated reading.")}</p>}
            <div className="space-y-1"><CalcLabel /><p className="text-sm text-muted-foreground">{t(r.overview)} {t("The Moon is in house {n} from your sign.", { n: r.moon_house })}</p></div>
          </section>
          <div className="grid sm:grid-cols-2 gap-4">{CATS.map(([id, l]) => <Category key={id} id={id} label={l} c={r.categories[id]} ai={r.ai?.[id]} />)}</div>
          <details className="rounded-2xl border p-4 text-sm">
            <summary data-testid="horoscope-transits-toggle" className="cursor-pointer min-h-10 flex items-center text-amber-200">{t("Planet positions used")}</summary>
            <ul data-testid="horoscope-transits" className="mt-2 grid grid-cols-2 sm:grid-cols-3 gap-2">
              {h.data.transits.map((p) => <li key={p.name} className="rounded-lg bg-card/60 px-3 py-2">{t(p.name)}: {t(p.sign)} {Math.floor(p.degree)}°{p.retrograde && !["Rahu", "Ketu"].includes(p.name) ? ` ${t("(R)")}` : ""}</li>)}
            </ul>
            <p className="mt-3 text-xs text-muted-foreground">{t(h.data.method)}</p>
          </details>
          <p className="text-xs text-muted-foreground">{t("Horoscopes are general guidance for everyone sharing a Moon sign, not personal predictions. For decisions about health, money or relationships, consult a qualified professional.")}</p>
        </div>
      )}
    </div>
  );
}
