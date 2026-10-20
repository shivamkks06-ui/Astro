import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { Menu, Sparkles, LogOut } from "lucide-react";
import { Sheet, SheetContent, SheetTrigger } from "./ui/sheet";
import { Button } from "./ui/button";
import { useAuth, homeFor } from "../context/AuthContext";

const DISCLAIMER = "Astrology services are offered as interpretive guidance, not guaranteed outcomes. They are not a substitute for professional medical, legal or financial advice.";

function NavLinks({ user, onNav }) {
  const links = [{ to: "/discover", label: "Find Astrologers" }, { to: "/legal/guidelines", label: "Safety & Guidelines" }];
  if (user) links.push({ to: homeFor(user), label: user.role === "admin" ? "Admin Console" : user.role === "astrologer" ? "Astrologer Studio" : "My Account" });
  return links.map((l) => (
    <NavLink key={l.to} to={l.to} onClick={onNav} data-testid={`nav-${l.to.replace(/\//g, "-").slice(1)}`}
      className={({ isActive }) => `text-base md:text-sm py-3 md:py-0 whitespace-nowrap transition-colors duration-200 ${isActive ? "text-amber-300" : "text-slate-300 hover:text-amber-200"}`}>
      {l.label}
    </NavLink>
  ));
}

function AuthButtons({ user, onNav }) {
  const { logout } = useAuth();
  const nav = useNavigate();
  if (user) {
    return (
      <Button data-testid="logout-button" variant="outline" size="sm" className="h-11 sm:h-8" onClick={async () => { onNav?.(); nav("/", { replace: true }); await logout(); }}>
        <LogOut className="h-4 w-4 mr-2" />Log out
      </Button>
    );
  }
  return (
    <div className="flex gap-2">
      <Button asChild variant="ghost" size="sm"><Link data-testid="nav-login" to="/login" onClick={onNav}>Log in</Link></Button>
      <Button asChild size="sm" className="rounded-full"><Link data-testid="nav-register" to="/register" onClick={onNav}>Join</Link></Button>
    </div>
  );
}

export function Header() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl bg-[#0B0F19]/80 border-b border-amber-500/10 pt-[env(safe-area-inset-top)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-8 h-14 sm:h-16 flex items-center justify-between gap-4">
        <Link to="/" data-testid="brand-logo" className="flex items-center gap-2 min-h-11">
          <Sparkles className="h-5 w-5 text-amber-400" />
          <span className="font-display text-lg tracking-wider text-amber-100">NakshatraVeda</span>
        </Link>
        <nav className="hidden md:flex items-center gap-8"><NavLinks user={user} /></nav>
        <div className="hidden md:block"><AuthButtons user={user} /></div>
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild className="md:hidden">
            <Button data-testid="mobile-menu-button" aria-label="Open menu" variant="ghost" size="icon"><Menu className="h-6 w-6" /></Button>
          </SheetTrigger>
          <SheetContent className="bg-card flex flex-col gap-2 pt-14 pb-[max(1.5rem,env(safe-area-inset-bottom))]">
            <NavLinks user={user} onNav={() => setOpen(false)} />
            <div className="pt-4"><AuthButtons user={user} onNav={() => setOpen(false)} /></div>
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
