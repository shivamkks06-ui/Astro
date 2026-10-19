import { Link } from "react-router-dom";
import { BadgeCheck, GraduationCap, Star } from "lucide-react";
import { inr } from "../lib/api";

export const Badges = ({ a, size = "sm" }) => (
  <div className="flex flex-wrap gap-2">
    {a.identity_verified && (
      <span data-testid="badge-identity-verified" title="Government identity checked by our team" className={`inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 px-2 py-0.5 ${size === "sm" ? "text-[11px]" : "text-xs"}`}>
        <BadgeCheck className="h-3.5 w-3.5" />Identity verified
      </span>
    )}
    {a.credential_verified && (
      <span data-testid="badge-credential-verified" title="Submitted qualification documents reviewed by our team" className={`inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 text-amber-300 px-2 py-0.5 ${size === "sm" ? "text-[11px]" : "text-xs"}`}>
        <GraduationCap className="h-3.5 w-3.5" />Credentials reviewed
      </span>
    )}
  </div>
);

export const Initials = ({ name, className = "h-14 w-14 text-lg" }) => (
  <div className={`rounded-full bg-gradient-to-br from-amber-500/30 to-indigo-900 border border-amber-500/30 flex items-center justify-center font-display text-amber-100 ${className}`}>
    {(name || "?").replace(/\[.*?\]/g, "").trim().split(" ").map((p) => p[0]).slice(0, 2).join("")}
  </div>
);

export function AstroCard({ a, i = 0 }) {
  return (
    <Link to={`/astrologers/${a.id}`} data-testid={`astrologer-card-${a.id}`} style={{ animationDelay: `${i * 60}ms` }}
      className="fade-up glass gold-border rounded-2xl p-6 flex flex-col gap-4 hover:-translate-y-1 transition-transform duration-300">
      <div className="flex items-center gap-4">
        <Initials name={a.display_name} />
        <div className="min-w-0">
          <h3 className="text-lg truncate">{a.display_name}</h3>
          <p className="text-xs text-muted-foreground">{a.experience_years} yrs · {a.languages.slice(0, 3).join(", ")}</p>
        </div>
      </div>
      <Badges a={a} />
      <p className="text-sm text-slate-300 line-clamp-2">{a.expertise.join(" · ")}</p>
      <div className="mt-auto flex items-center justify-between text-sm">
        <span className="flex items-center gap-1 text-amber-300"><Star className="h-4 w-4 fill-amber-400 text-amber-400" />{a.rating_count ? `${a.rating_avg} (${a.rating_count})` : "New"}</span>
        <span className="text-slate-200">Chat {inr(a.rates.chat)}/min</span>
      </div>
    </Link>
  );
}
