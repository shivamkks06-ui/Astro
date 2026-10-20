import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { Menu, LogOut, ShieldCheck } from "lucide-react";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "./ui/sheet";
import { Button } from "./ui/button";
import { useAuth, homeFor } from "../context/AuthContext";

export const BrandMark = ({ className = "" }) => <img src="/brand-mark.png" alt="" aria-hidden="true" width={64} height={64} className={`${className} rounded-full shrink-0`} />;

const DISCLAIMER = "Astrology services are offered as interpretive guidance, not guaranteed outcomes. They are not a substitute for professional medical, legal or financial advice.";

function NavLinks({ user, onNav, drawer }) {
  const links = [{ to: "/discover", label: "Find Astrologers" }, { to: "/legal/guidelines", label: "Safety & Guidelines" }];
  if (user) links.push({ to: homeFor(user), label: user.role === "admin" ? "Admin Console" : user.role === "astrologer" ? "Astrologer Studio" : "My Account" });
  return links.map((l) => (
    <NavLink key={l.to} to={l.to} onClick={onNav} data-testid={`nav-${l.to.replace(/\//g, "-").slice(1)}`}
      className={({ isActive }) => `${drawer ? "flex items-center min-h-12 px-3 rounded-lg text-base active:bg-amber-500/10" : "text-sm"} whitespace-nowrap transition-colors duration-200 ${isActive ? "text-amber-300" + (drawer ? " bg-amber-500/10" : "") : "text-slate-200 hover:text-amber-200"}`}>
      {l.label}
    </NavLink>
  ));
}

function AuthButtons({ user, onNav, drawer }) {
  const { logout } = useAuth();
  const nav = useNavigate();
  if (user) {
    return (
      <Button data-testid="logout-button" variant="outline" size="sm" className={drawer ? "w-full h-12 rounded-full" : "h-11 sm:h-8"} onClick={async () => { onNav?.(); nav("/", { replace: true }); await logout(); }}>
        <LogOut className="h-4 w-4 mr-2" />Log out
      </Button>
    );
  }
  return (
    <div className={drawer ? "flex flex-col gap-3" : "flex gap-2"}>
      <Button asChild variant={drawer ? "outline" : "ghost"} size="sm" className={drawer ? "w-full h-12 rounded-full" : ""}><Link data-testid="nav-login" to="/login" onClick={onNav}>Log in</Link></Button>
      <Button asChild size="sm" className={`rounded-full ${drawer ? "w-full h-12" : ""}`}><Link data-testid="nav-register" to="/register" onClick={onNav}>Join</Link></Button>
    </div>
  );
}

export function Header() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl bg-[#0B1225]/85 border-b border-amber-500/10 pt-[env(safe-area-inset-top)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-8 h-14 sm:h-16 flex items-center justify-between gap-4">
        <Link to="/" data-testid="brand-logo" aria-label="NakshatraVeda home" className="flex items-center gap-2.5 min-h-11">
          <BrandMark className="h-8 w-8" />
          <span className="flex flex-col leading-none">
            <span className="font-display text-[15px] sm:text-lg tracking-[0.14em] text-amber-200">NAKSHATRAVEDA</span>
            <span className="hidden sm:block mt-1 text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Verified Vedic Astrologers</span>
          </span>
        </Link>
        <nav className="hidden md:flex items-center gap-8"><NavLinks user={user} /></nav>
        <div className="hidden md:block"><AuthButtons user={user} /></div>
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild className="md:hidden">
            <Button data-testid="mobile-menu-button" aria-label="Open menu" variant="ghost" size="icon"><Menu className="h-6 w-6" /></Button>
          </SheetTrigger>
          <SheetContent data-testid="mobile-drawer" aria-describedby={undefined} onOpenAutoFocus={(e) => e.preventDefault()} className="bg-card flex flex-col gap-0 p-0 overflow-y-auto pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]">
            <SheetTitle className="flex items-center gap-2 h-16 px-5 pr-14 border-b border-amber-500/10 text-left">
              <BrandMark className="h-7 w-7" /><span className="font-display text-base tracking-[0.14em] text-amber-200">NAKSHATRAVEDA</span>
            </SheetTitle>
            <nav aria-label="Main" className="flex flex-col gap-1 p-3"><NavLinks drawer user={user} onNav={() => setOpen(false)} /></nav>
            <div className="px-3 pt-2"><AuthButtons drawer user={user} onNav={() => setOpen(false)} /></div>
            <div data-testid="drawer-trust-card" className="mt-auto m-3 rounded-xl border border-amber-500/20 bg-[#0B1225]/60 p-4 space-y-1.5">
              <p className="flex items-center gap-2 text-sm text-amber-200"><ShieldCheck className="h-4 w-4" />Identity-checked astrologers</p>
              <p className="text-xs leading-relaxed text-muted-foreground">Guidance only, never guaranteed outcomes. Clear per-minute prices and refund terms.</p>
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-amber-500/10 mt-14 sm:mt-24 pb-[env(safe-area-inset-bottom)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-8 py-8 sm:py-10 grid grid-cols-1 gap-4 sm:gap-6 md:grid-cols-[2fr_1fr]">
        <p data-testid="footer-disclaimer" className="text-sm text-muted-foreground leading-relaxed max-w-2xl">{DISCLAIMER}</p>
        <div className="flex flex-wrap gap-x-6 text-sm md:justify-end">
          {[["terms", "Terms"], ["privacy", "Privacy"], ["guidelines", "Community Guidelines"], ["refunds", "Refund Policy"]].map(([s, l]) => (
            <Link key={s} to={`/legal/${s}`} data-testid={`footer-link-${s}`} className="py-2 text-slate-400 hover:text-amber-200">{l}</Link>
          ))}
        </div>
      </div>
    </footer>
  );
}

export const Disclaimer = () => (
  <div data-testid="guidance-disclaimer" className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-[13px] leading-relaxed text-amber-100/80">{DISCLAIMER}</div>
);
