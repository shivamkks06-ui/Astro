import { useState } from "react";
import { Link } from "react-router-dom";
import { RotateCcw, Heart } from "lucide-react";
import { toast } from "sonner";
import { BirthForm } from "../components/kundli/BirthForm";
import { api, errMsg } from "../lib/api";
import { useLang } from "../lib/i18n";
import { LangToggle } from "../components/LangToggle";

const BAND = { Excellent: "text-emerald-300", Good: "text-emerald-300", Average: "text-amber-200", Low: "text-orange-300" };
const mStatus = (m, t) => (!m.manglik ? t("Not Manglik") : m.cancellations.length ? `${t("Manglik, traditionally cancelled")} (${m.cancellations.map((c) => t(c)).join("; ")})` : t("Manglik"));

function Result({ data, onReset }) {
  const { t, tp } = useLang();
  const r = data.result;
  return (
    <section data-testid="match-result" className="space-y-6">
      <div className="glass rounded-2xl p-5 sm:p-7 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="overline mb-1">{t("Ashtakoota Guna Milan")}</p>
          <p data-testid="match-total" className="font-serif text-5xl text-amber-100">{r.total}<span className="text-2xl text-muted-foreground"> / 36</span></p>
          <p data-testid="match-band" className={`mt-1 font-semibold ${BAND[r.band]}`}>{t("{band} agreement", { band: t(r.band) })}</p>
        </div>
        <button type="button" data-testid="match-reset" onClick={onReset} className="inline-flex items-center gap-1.5 min-h-11 px-3 text-sm text-amber-200"><RotateCcw className="h-4 w-4" />{t("New match")}</button>
      </div>
      <div className="rounded-xl border overflow-hidden">
        <table data-testid="match-table" className="w-full text-sm">
          <thead className="bg-secondary/60 text-left text-xs uppercase tracking-wider text-muted-foreground"><tr><th className="px-3 py-2.5">{t("Koota")} <span className="normal-case tracking-normal">{t("(boy / girl)")}</span></th><th className="px-3 py-2.5 text-right">{t("Score")}</th></tr></thead>
          <tbody>
            {r.kootas.map((k) => (
              <tr key={k.name} data-testid={`match-koota-${k.name.toLowerCase().replace(/\s/g, "-")}`} className="border-t border-border/60">
                <td className="px-3 py-2.5"><span className="font-medium">{t(k.name)}</span><span className="block text-xs text-muted-foreground">{tp(k.detail)}</span></td>
                <td className={`px-3 py-2.5 text-right font-mono whitespace-nowrap ${k.score === 0 ? "text-orange-300" : ""}`}>{k.score} / {k.max}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        {[["boy", "Boy"], ["girl", "Girl"]].map(([k, l]) => (
          <div key={k} data-testid={`match-${k}-card`} className="rounded-xl border p-4 text-sm space-y-1">
            <p className="font-semibold text-amber-100">{t(l)}{data[k].name ? `: ${data[k].name}` : ""}</p>
            <p className="text-muted-foreground">{t("Moon")} {t(r[k].moon_sign)} · {t(r[k].nakshatra)}</p>
            <p>{mStatus(r[k].manglik, t)}</p>
          </div>
        ))}
      </div>
      {(r.nadi_dosha || r.bhakoot_dosha) && <p data-testid="match-doshas" className="text-sm text-orange-200">{t("Traditional doshas present")}: {[r.nadi_dosha && t("Nadi dosha"), r.bhakoot_dosha && t("Bhakoot dosha")].filter(Boolean).join(", ")}{t(".")} {t("Astrologers often check further rules before reading these.")}</p>}
      <p className="text-xs text-muted-foreground">{t("Guna Milan is a traditional compatibility score calculated from both Moon positions. It is guidance, not a prediction about any marriage.")} {t("For a full reading,")} <Link to="/discover" className="text-amber-200 underline">{t("consult a verified astrologer")}</Link>{t(".")}</p>
    </section>
  );
}

export default function Match() {
  const { t } = useLang();
  const [boy, setBoy] = useState(null);
  const [draft, setDraft] = useState(null);
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const run = async (girl) => {
    setBusy(true);
    try { const { data: d } = await api.post("/kundli/match", { boy, girl }); setData(d); window.scrollTo({ top: 0, behavior: "smooth" }); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <div className="max-w-4xl mx-auto px-5 sm:px-8 py-8 sm:py-12 space-y-8">
      <header>
        <div className="flex flex-wrap items-center justify-between gap-3 mb-2"><p className="overline flex items-center gap-1.5"><Heart className="h-3.5 w-3.5" />{t("Kundli matching")}</p><LangToggle /></div>
        <h1 className="text-[1.875rem] leading-tight sm:text-5xl">{t("36 Guna Milan")}</h1>
        <p className="mt-3 text-sm sm:text-base text-muted-foreground">{t("Enter both birth details. Traditional Ashtakoota uses the boy's and the girl's roles.")}</p>
      </header>
      {data ? <Result data={data} onReset={() => { setData(null); setBoy(null); setDraft(null); }} /> : (
        <div className="space-y-3">
          <p data-testid="match-step" className="text-sm font-semibold text-amber-200">{t(boy ? "Step 2 of 2: Girl's details" : "Step 1 of 2: Boy's details")}</p>
          {boy && <button type="button" data-testid="match-back" onClick={() => { setDraft(boy); setBoy(null); }} className="text-sm text-muted-foreground underline min-h-11">{t("Edit boy's details")} ({boy.date}, {boy.place.split(",")[0]})</button>}
          <BirthForm key={boy ? "girl" : "boy"} initial={boy ? null : draft} busy={busy} submitLabel={t(boy ? "Check match" : "Next: girl's details")} onSubmit={boy ? run : setBoy} />
        </div>
      )}
    </div>
  );
}
