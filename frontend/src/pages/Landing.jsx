import { Link } from "react-router-dom";
import { ShieldCheck, ScrollText, Scale } from "lucide-react";
import { Button } from "../components/ui/button";
import { AstroCard } from "../components/AstroCard";
import { Loading, ErrorState, Empty } from "../components/States";
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
        <img src="/hero.jpg" alt="" aria-hidden="true" className="absolute inset-0 h-full w-full object-cover opacity-40" />
        <div className="absolute inset-0 bg-gradient-to-b from-[#0B0F19]/40 via-[#0B0F19]/70 to-[#0B0F19]" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-8 py-24 sm:py-32 grid md:grid-cols-12 gap-8">
          <div className="md:col-span-8 fade-up">
            <p className="overline mb-6">Verified Vedic astrology marketplace</p>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl leading-[1.08]">Consult astrologers <span className="text-amber-300">whose identity we have checked</span>.</h1>
            <p className="mt-6 text-base md:text-lg text-slate-300 max-w-xl">Book chat consultations at clear per-minute rates. Astrology here is interpretive guidance only, never a promise about marriage, health, money or any other outcome.</p>
            <div className="mt-10 flex flex-wrap gap-4">
              <Button asChild size="lg" className="rounded-full px-8"><Link data-testid="hero-discover-button" to="/discover">Find an astrologer</Link></Button>
              <Button asChild size="lg" variant="outline" className="rounded-full px-8"><Link data-testid="hero-join-astrologer-button" to="/register?role=astrologer">Join as astrologer</Link></Button>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-8 py-20 grid md:grid-cols-3 gap-6">
        {PILLARS.map(({ icon: I, t, d }, i) => (
          <div key={t} className="fade-up rounded-2xl border p-8 bg-card/60" style={{ animationDelay: `${i * 80}ms` }}>
            <I className="h-6 w-6 text-amber-400 mb-5" />
            <h3 className="text-xl mb-2">{t}</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">{d}</p>
          </div>
        ))}
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-8">
        <div className="flex items-end justify-between mb-8">
          <div><p className="overline mb-2">Listed now</p><h2 className="text-2xl sm:text-3xl">Available astrologers</h2></div>
          <Link to="/discover" data-testid="landing-view-all" className="text-sm text-amber-300 hover:underline">View all</Link>
        </div>
        {loading ? <Loading /> : error ? <ErrorState error={error} onRetry={reload} /> : data.items.length === 0 ? (
          <Empty title="No astrologers listed yet" hint="Verified astrologers will appear here once their listing is active." />
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">{data.items.map((a, i) => <AstroCard key={a.id} a={a} i={i} />)}</div>
        )}
      </section>
    </div>
  );
}
