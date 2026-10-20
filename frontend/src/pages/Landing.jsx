import { Link } from "react-router-dom";
import { ShieldCheck, ScrollText, Scale } from "lucide-react";
import { Button } from "../components/ui/button";
import { AstroCard } from "../components/AstroCard";
import { CardSkeletons, ErrorState, Empty } from "../components/States";
import { useApi } from "../lib/useApi";

const PILLARS = [
  { icon: ShieldCheck, t: "Identity checks", d: "Every listed astrologer's government ID is reviewed by our team before they can appear publicly." },
  { icon: ScrollText, t: "Credentials reviewed separately", d: "Qualification documents get a separate review. We only show that badge after the check is done." },
  { icon: Scale, t: "Clear prices and refunds", d: "You see the full price and refund terms before you pay. Unconnected sessions are not charged." },
];

export default function Landing() {
  const { data, loading, error, reload } = useApi("/astrologers?limit=3");
  return (
    <div>
      <section className="relative overflow-hidden">
        <img src="/hero.jpg" alt="" aria-hidden="true" decoding="async" fetchpriority="high" className="absolute inset-0 h-full w-full object-cover opacity-40" />
        <div className="absolute inset-0 bg-gradient-to-b from-[#0B0F19]/40 via-[#0B0F19]/70 to-[#0B0F19]" />
        <div className="relative max-w-7xl mx-auto px-5 sm:px-8 pt-10 pb-12 sm:py-24 lg:py-32 grid md:grid-cols-12 gap-8">
          <div className="md:col-span-8 fade-up">
            <p className="overline mb-4 sm:mb-6">Verified Vedic astrology marketplace</p>
            <h1 className="text-[1.875rem] leading-[1.15] sm:text-5xl lg:text-6xl sm:leading-[1.08] text-balance">Consult astrologers <span className="text-amber-300">whose identity we have checked</span>.</h1>
            <p className="mt-4 sm:mt-6 text-[15px] leading-relaxed md:text-lg text-slate-300 max-w-xl">Book chat consultations at clear per-minute rates. Astrology here is interpretive guidance only, never a promise about marriage, health, money or any other outcome.</p>
            <div className="mt-7 sm:mt-10 flex flex-col sm:flex-row gap-3 sm:gap-4">
              <Button asChild size="lg" className="rounded-full px-8 h-12 text-base w-full sm:w-auto"><Link data-testid="hero-discover-button" to="/discover">Find an astrologer</Link></Button>
              <Button asChild size="lg" variant="outline" className="rounded-full px-8 h-12 text-base w-full sm:w-auto"><Link data-testid="hero-join-astrologer-button" to="/register?role=astrologer">Join as astrologer</Link></Button>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-5 sm:px-8 pt-2 pb-10 sm:py-20 grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
        {PILLARS.map(({ icon: I, t, d }, i) => (
          <div key={t} data-testid={`trust-pillar-${i}`} className="fade-up rounded-2xl border p-5 sm:p-8 bg-card/60 flex gap-4 md:block" style={{ animationDelay: `${i * 80}ms` }}>
            <I className="h-6 w-6 shrink-0 text-amber-400 mt-0.5 md:mb-5 md:mt-0" />
            <div>
              <h3 className="text-lg sm:text-xl mb-1.5 sm:mb-2">{t}</h3>
              <p className="text-sm sm:text-[15px] text-muted-foreground leading-relaxed">{d}</p>
            </div>
          </div>
        ))}
      </section>

      <section className="max-w-7xl mx-auto px-5 sm:px-8">
        <div className="flex items-end justify-between gap-4 mb-5 sm:mb-8">
          <div><p className="overline mb-2">Listed now</p><h2 className="text-[1.375rem] sm:text-3xl">Available astrologers</h2></div>
          <Link to="/discover" data-testid="landing-view-all" className="text-sm text-amber-300 hover:underline py-3 shrink-0">View all</Link>
        </div>
        {loading ? <CardSkeletons /> : error ? <ErrorState error={error} onRetry={reload} /> : !data?.items?.length ? (
          <Empty title="No astrologers listed yet" hint="Verified astrologers will appear here once their listing is active." />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">{data.items.map((a, i) => <AstroCard key={a.id} a={a} i={i} />)}</div>
        )}
      </section>
    </div>
  );
}
