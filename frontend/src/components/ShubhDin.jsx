import { Link } from "react-router-dom";
import { Sunrise, Moon, Sparkles, ChevronRight } from "lucide-react";
import { useApi } from "../lib/useApi";
import { useLang } from "../lib/i18n";

const HI = { "Today's Shubh Din": "आज का शुभ दिन", Tithi: "तिथि", Nakshatra: "नक्षत्र", "Abhijit Muhurat": "अभिजीत मुहूर्त", "Brahma Muhurat": "ब्रह्म मुहूर्त", "Full Panchang": "पूरा पंचांग", "Times for New Delhi (IST), calculated from real Sun and Moon positions.": "समय नई दिल्ली (IST) के लिए, सूर्य और चंद्र की वास्तविक स्थिति से गणना।" };

function Cell({ icon: I, label, value, id }) {
  return (
    <div className="flex items-start gap-3 min-w-0">
      <I className="h-5 w-5 shrink-0 text-amber-300 mt-0.5" />
      <div className="min-w-0"><p className="text-[11px] uppercase tracking-wider text-amber-200/70">{label}</p><p data-testid={`shubh-${id}`} className="text-amber-50 font-semibold break-words">{value}</p></div>
    </div>
  );
}

export function ShubhDin() {
  const { data } = useApi("/panchang/today");
  const { t, lang, locale } = useLang();
  if (!data) return null;
  const L = (s) => (lang === "hi" && HI[s]) || s;
  const m = data.muhurta;
  const day = new Date(`${data.date}T12:00:00`).toLocaleDateString(locale, { weekday: "long", day: "numeric", month: "long" });
  return (
    <section className="max-w-7xl mx-auto px-5 sm:px-8 pt-6">
      <div data-testid="shubh-din-card" className="fade-up relative overflow-hidden rounded-2xl border border-amber-400/40 p-5 sm:p-7 bg-gradient-to-br from-[#3a2a08]/80 via-[#1a1a2e]/90 to-[#0B1225]">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-5">
          <div><p className="overline">{L("Today's Shubh Din")}</p><p data-testid="shubh-date" className="font-serif text-xl text-amber-100 mt-1">{day}</p></div>
          <Link to="/kundli" data-testid="shubh-panchang-link" className="inline-flex items-center gap-1 text-sm text-amber-300 hover:text-amber-200 min-h-11">{L("Full Panchang")}<ChevronRight className="h-4 w-4" /></Link>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
          <Cell id="tithi" icon={Moon} label={L("Tithi")} value={`${t(data.paksha)} ${t(data.tithi)}`} />
          <Cell id="nakshatra" icon={Sparkles} label={L("Nakshatra")} value={t(data.nakshatra)} />
          {m && <Cell id="abhijit" icon={Sparkles} label={L("Abhijit Muhurat")} value={m.abhijit.join(" – ")} />}
          {m && <Cell id="brahma" icon={Sunrise} label={L("Brahma Muhurat")} value={m.brahma.join(" – ")} />}
        </div>
        <p className="mt-5 text-xs text-muted-foreground">{L("Times for New Delhi (IST), calculated from real Sun and Moon positions.")}</p>
      </div>
    </section>
  );
}
