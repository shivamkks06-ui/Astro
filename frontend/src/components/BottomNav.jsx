import { NavLink, useLocation } from "react-router-dom";
import { Home, Compass, CalendarCheck, LayoutDashboard, Shield, LogIn } from "lucide-react";
import { useAuth, homeFor } from "../context/AuthContext";
import { haptic } from "../lib/native";

// detail screens have their own bottom action bar or input, so the tab bar steps aside there
const HIDDEN = [/^\/astrologers\//, /^\/bookings\//, /^\/pay\//, /^\/login/, /^\/register/];
export const showsBottomNav = (path) => !HIDDEN.some((r) => r.test(path));

export function BottomNav() {
  const { user } = useAuth();
  const { pathname } = useLocation();
  if (!showsBottomNav(pathname)) {
    // the profile's sticky book bar needs the same room so the footer links stay tappable
    return /^\/astrologers\//.test(pathname) ? <div aria-hidden="true" data-testid="profile-bar-spacer" className="lg:hidden h-[76px] pb-[env(safe-area-inset-bottom)] box-content" /> : null;
  }
  const own = !user ? { to: "/login", label: "Log in", icon: LogIn }
    : user.role === "admin" ? { to: "/admin", label: "Admin", icon: Shield }
      : user.role === "astrologer" ? { to: "/studio", label: "Studio", icon: LayoutDashboard }
        : { to: homeFor(user), label: "Bookings", icon: CalendarCheck };
  const items = [{ to: "/", label: "Home", icon: Home, end: true }, { to: "/discover", label: "Discover", icon: Compass }, own];
  return (
    <>
    <div aria-hidden="true" className="md:hidden h-[65px] pb-[env(safe-area-inset-bottom)] box-content" />
    <nav data-testid="bottom-nav" aria-label="Main" className="md:hidden fixed inset-x-0 bottom-0 z-40 border-t border-amber-500/15 bg-[#0B0F19]/95 backdrop-blur pb-[env(safe-area-inset-bottom)]">
      <div className="grid grid-cols-3 h-16">
        {items.map(({ to, label, icon: I, end }) => (
          <NavLink key={to} to={to} end={end} replace={pathname === to} onClick={() => haptic()} data-testid={`bottom-nav-${label.toLowerCase().replace(/\s/g, "-")}`}
            className={({ isActive }) => `flex flex-col items-center justify-center gap-1 text-xs select-none transition-colors duration-150 active:bg-amber-500/10 ${isActive ? "text-amber-300" : "text-slate-400"}`}>
            {({ isActive }) => (<><span className={`rounded-full px-4 py-1 transition-colors duration-150 ${isActive ? "bg-amber-500/15" : ""}`}><I className="h-5 w-5" /></span>{label}</>)}
          </NavLink>
        ))}
      </div>
    </nav>
    </>
  );
}
