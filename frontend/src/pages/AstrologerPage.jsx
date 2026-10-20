import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { MessageCircle, Phone, Video, Star, Flag, Ban, Briefcase, CalendarClock, IndianRupee } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Badges, Avatar } from "../components/AstroCard";
import { ProfileSkeleton, ErrorState, Empty } from "../components/States";
import { Disclaimer } from "../components/Layout";
import { BookDialog } from "../components/BookDialog";
import { LoginSheet } from "../components/LoginSheet";
import { ReportBlock } from "../components/ReportBlock";
import { useApi } from "../lib/useApi";
import { inr, fmtDate } from "../lib/api";
import { haptic } from "../lib/native";
import { useAuth } from "../context/AuthContext";

const MODE_ICON = { chat: MessageCircle, audio: Phone, video: Video };

function Rates({ a, calls, mode, setMode }) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {["chat", "audio", "video"].map((m) => {
        const I = MODE_ICON[m];
        const offered = a.modes_enabled.includes(m) && a.rates[m] > 0;
        const callOff = m !== "chat" && !calls.operational;
        const disabled = !offered || callOff;
        return (
          <button key={m} disabled={disabled} onClick={() => setMode(m)} data-testid={`mode-${m}`} aria-pressed={mode === m}
            className={`rounded-xl border p-3 sm:p-4 text-left min-h-[88px] transition-[transform,border-color,background-color] duration-150 active:scale-[0.97] ${mode === m ? "border-amber-400 bg-amber-500/10" : "bg-card"} ${disabled ? "opacity-50 cursor-not-allowed" : "hover:border-amber-400/60"}`}>
            <I className="h-5 w-5 text-amber-400 mb-2" />
            <p className="capitalize text-sm font-medium">{m}</p>
            <p className="text-xs text-muted-foreground">{!offered ? "Not offered" : callOff ? "Not yet operational" : `${inr(a.rates[m])}/min`}</p>
          </button>
        );
      })}
    </div>
  );
}

function Slots({ slots, slot, setSlot }) {
  if (!slots.length) return <Empty title="No open slots" hint="Check back later for new availability." />;
  return (
    <div id="slots" className="flex flex-wrap gap-2 scroll-mt-24">
      {slots.map((s) => (
        <button key={s.id} data-testid={`slot-${s.id}`} onClick={() => setSlot(s)} aria-pressed={slot?.id === s.id}
          className={`min-h-11 rounded-lg border px-3 py-2 text-[13px] transition-[transform,border-color,background-color] duration-150 active:scale-[0.97] ${slot?.id === s.id ? "border-amber-400 bg-amber-500/10 text-amber-200" : "bg-card hover:border-amber-400/60"}`}>
          {fmtDate(s.start_at)} · {s.duration_min}m
        </button>
      ))}
    </div>
  );
}

const Stat = ({ icon: I, label, value, testid }) => (
  <div data-testid={testid} className="rounded-xl border bg-card/70 px-3 py-2.5">
    <p className="flex items-center gap-1.5 text-xs text-muted-foreground"><I className="h-3.5 w-3.5 text-amber-400" />{label}</p>
    <p className="text-sm font-medium mt-0.5 truncate">{value}</p>
  </div>
);

const go = (id) => document.getElementById(id)?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });

function SectionNav({ reviews }) {
  return (
    <nav aria-label="Profile sections" className="sticky top-14 sm:top-16 z-30 -mx-5 px-5 py-2 bg-[#0B0F19]/95 border-b border-amber-500/10 flex gap-2 lg:hidden">
      {[["about", "About"], ["reviews", `Reviews (${reviews})`], ["book", "Book"]].map(([k, l]) => (
        <button key={k} data-testid={`profile-tab-${k}`} onClick={() => go(k)} className="min-h-10 rounded-full border px-4 text-[13px] active:bg-amber-500/10">{l}</button>
      ))}
    </nav>
  );
}

export default function AstrologerPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const nav = useNavigate();
  const { data: a, loading, error, reload } = useApi(`/astrologers/${id}`);
  const cfg = useApi("/public/config");
  const [mode, setMode] = useState("chat");
  const [slot, setSlot] = useState(null);
  const [loginOpen, setLoginOpen] = useState(false);
  const [bookOpen, setBookOpen] = useState(false);
  if (loading || cfg.loading) return <ProfileSkeleton />;
  if (error) return <div className="max-w-3xl mx-auto px-4 py-16"><ErrorState error={error} onRetry={reload} /></div>;
  const calls = cfg.data?.calls || { operational: false };
  const offered = ["chat", "audio", "video"].filter((m) => a.modes_enabled.includes(m) && a.rates[m] > 0);
  const fromRate = offered.length ? Math.min(...offered.map((m) => a.rates[m])) : null;

  const startBooking = () => {
    haptic();
    if (!user) return setLoginOpen(true);
    if (user.role !== "customer") return toast.error("Only customer accounts can book consultations");
    if (!slot) {
      toast.message("Choose a time slot first");
      return go("slots");
    }
    setBookOpen(true);
  };
  const pickMode = (m) => {
    setMode(m);
    if (!user) setLoginOpen(true);
  };
  const cta = !user ? "Log in to book" : slot ? "Review & request booking" : "Choose a slot";

  return (
    <div className="max-w-6xl mx-auto px-5 sm:px-8 pt-5 pb-6 lg:pb-12 sm:pt-10 grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-6 lg:gap-10">
      <div className="space-y-6 min-w-0">
        <div id="about" className="flex items-center gap-4 sm:gap-5 scroll-mt-28">
          <Avatar a={a} className="h-20 w-20 sm:h-24 sm:w-24 text-2xl" />
          <div className="space-y-1.5 min-w-0">
            <h1 data-testid="astrologer-name" className="text-[1.625rem] leading-tight sm:text-4xl">{a.display_name}</h1>
            <p className="text-[13px] text-muted-foreground">{a.languages.join(", ")}</p>
            <Badges a={a} size="md" />
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <Stat icon={Briefcase} label="Experience" value={`${a.experience_years} years`} testid="stat-experience" />
          <Stat icon={Star} label="Rating" value={a.rating_count ? `${a.rating_avg} · ${a.rating_count} reviews` : "No reviews yet"} testid="stat-rating" />
          <Stat icon={CalendarClock} label="Next slot" value={a.slots[0] ? fmtDate(a.slots[0].start_at) : "None open"} testid="stat-next-slot" />
          <Stat icon={IndianRupee} label="From" value={fromRate ? `${inr(fromRate)}/min` : "—"} testid="stat-price" />
        </div>
        <SectionNav reviews={a.reviews.length} />
        <p className="text-[15px] text-slate-300 leading-relaxed whitespace-pre-line">{a.bio}</p>
        <div className="flex flex-wrap gap-2">{a.expertise.map((e) => <span key={e} className="rounded-full border px-3 py-1 text-xs">{e}</span>)}</div>
        {a.credential_summary && <p className="text-sm text-muted-foreground">Stated qualifications: {a.credential_summary}{!a.credential_verified && " (not yet reviewed)"}</p>}
        <Disclaimer />
        <section id="reviews" className="scroll-mt-28">
          <h2 className="text-lg sm:text-xl mb-3 sm:mb-4 flex items-center gap-2"><Star className="h-5 w-5 text-amber-400" />Reviews from completed consultations</h2>
          {a.reviews.length === 0 ? <p className="text-sm text-muted-foreground">No reviews yet.</p> : (
            <div className="space-y-3">{a.reviews.map((r) => (
              <div key={r.id} data-testid={`review-${r.id}`} className="rounded-xl border p-4 bg-card/60">
                <p className="text-sm text-amber-300" aria-label={`${r.rating} out of 5`}>{"★".repeat(r.rating)}<span className="text-slate-600">{"★".repeat(5 - r.rating)}</span></p>
                <p className="text-sm mt-1">{r.comment}</p>
                <p className="text-xs text-muted-foreground mt-2">{r.customer_name} · {fmtDate(r.created_at)}</p>
              </div>))}
            </div>
          )}
        </section>
        {user?.role === "customer" && (
          <div className="flex gap-3">
            <ReportBlock targetId={a.id} trigger={<Button variant="ghost" size="sm" data-testid="report-astrologer"><Flag className="h-4 w-4 mr-2" />Report</Button>} mode="report" />
            <ReportBlock targetId={a.id} trigger={<Button variant="ghost" size="sm" data-testid="block-astrologer"><Ban className="h-4 w-4 mr-2" />Block</Button>} mode="block" />
          </div>
        )}
      </div>
      <aside id="book" className="glass rounded-2xl p-5 sm:p-6 space-y-5 h-fit lg:sticky lg:top-24 scroll-mt-28">
        <h2 className="text-lg sm:text-xl">Book a consultation</h2>
        <Rates a={a} calls={calls} mode={mode} setMode={pickMode} />
        {!calls.operational && <p data-testid="calls-not-operational" className="text-xs text-muted-foreground">Audio and video calls aren't available yet. Chat consultations are open.</p>}
        <Slots slots={a.slots} slot={slot} setSlot={setSlot} />
        <Button data-testid="book-now-button" className="w-full rounded-full h-12 sm:h-10" onClick={startBooking}>{cta}</Button>
        {slot && <p className="text-[13px] text-center text-muted-foreground" data-testid="selected-slot-summary">{fmtDate(slot.start_at)} · {slot.duration_min} min · {inr(a.rates[mode] * slot.duration_min)} total</p>}
      </aside>
      <div className="lg:hidden fixed inset-x-0 bottom-0 z-40 border-t border-amber-500/15 bg-[#0B0F19]/95 backdrop-blur px-5 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] flex items-center gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-[13px] text-muted-foreground"><span className="capitalize">{mode}</span> {a.rates[mode] > 0 ? `· ${inr(a.rates[mode])}/min` : ""}</p>
          <p className="text-sm truncate">{slot ? `${fmtDate(slot.start_at)} · ${slot.duration_min}m` : a.slots.length ? "Pick a time slot" : "No open slots"}</p>
        </div>
        <Button data-testid="mobile-book-bar-button" className="rounded-full h-12 px-6 shrink-0" onClick={startBooking}>{!user ? "Log in" : slot ? "Book" : "Choose slot"}</Button>
      </div>
      {user?.role === "customer" && slot && <BookDialog a={a} slot={slot} mode={mode} policy={cfg.data.policy} open={bookOpen} onOpenChange={setBookOpen} onBooked={(b) => nav(`/bookings/${b.id}`)} />}
      <LoginSheet open={loginOpen} onOpenChange={setLoginOpen} next={`/astrologers/${id}`} reason={`Log in to book ${a.display_name}. You'll stay on this profile.`} />
    </div>
  );
}
