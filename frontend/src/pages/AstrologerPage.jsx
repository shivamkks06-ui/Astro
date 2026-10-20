import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { MessageCircle, Phone, Video, Star, Flag, Ban } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Badges, Initials } from "../components/AstroCard";
import { Loading, ErrorState, Empty } from "../components/States";
import { Disclaimer } from "../components/Layout";
import { BookDialog } from "../components/BookDialog";
import { ReportBlock } from "../components/ReportBlock";
import { useApi } from "../lib/useApi";
import { inr, fmtDate } from "../lib/api";
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
          <button key={m} disabled={disabled} onClick={() => setMode(m)} data-testid={`mode-${m}`}
            className={`rounded-xl border p-4 text-left transition-colors duration-200 ${mode === m ? "border-amber-400 bg-amber-500/10" : "bg-card"} ${disabled ? "opacity-50 cursor-not-allowed" : "hover:border-amber-400/60"}`}>
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
    <div className="flex flex-wrap gap-2">
      {slots.map((s) => (
        <button key={s.id} data-testid={`slot-${s.id}`} onClick={() => setSlot(s)}
          className={`min-h-11 rounded-lg border px-3 py-2 text-[13px] transition-colors duration-200 ${slot?.id === s.id ? "border-amber-400 bg-amber-500/10 text-amber-200" : "bg-card hover:border-amber-400/60"}`}>
          {fmtDate(s.start_at)} · {s.duration_min}m
        </button>
      ))}
    </div>
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
  if (loading || cfg.loading) return <Loading />;
  if (error) return <div className="max-w-3xl mx-auto px-4 py-16"><ErrorState error={error} onRetry={reload} /></div>;
  const calls = cfg.data?.calls || { operational: false };

  const startBooking = () => {
    if (!user) return nav(`/login?next=/astrologers/${id}`, { state: { from: `/astrologers/${id}` } });
    if (user.role !== "customer") return toast.error("Only customer accounts can book consultations");
    if (!slot) return toast.error("Please choose a time slot");
  };

  return (
    <div className="max-w-6xl mx-auto px-5 sm:px-8 py-6 sm:py-12 grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-6 sm:gap-10">
      <div className="space-y-8">
        <div className="flex items-start gap-5">
          <Initials name={a.display_name} className="h-20 w-20 text-2xl" />
          <div className="space-y-2">
            <h1 data-testid="astrologer-name" className="text-3xl sm:text-4xl">{a.display_name}</h1>
            <p className="text-sm text-muted-foreground">{a.experience_years} years · {a.languages.join(", ")}</p>
            <Badges a={a} size="md" />
          </div>
        </div>
        <p className="text-slate-300 leading-relaxed whitespace-pre-line">{a.bio}</p>
        <div className="flex flex-wrap gap-2">{a.expertise.map((e) => <span key={e} className="rounded-full border px-3 py-1 text-xs">{e}</span>)}</div>
        {a.credential_summary && <p className="text-sm text-muted-foreground">Stated qualifications: {a.credential_summary}{!a.credential_verified && " (not yet reviewed)"}</p>}
        <Disclaimer />
        <div>
          <h2 className="text-xl mb-4 flex items-center gap-2"><Star className="h-5 w-5 text-amber-400" />Reviews from completed consultations</h2>
          {a.reviews.length === 0 ? <p className="text-sm text-muted-foreground">No reviews yet.</p> : (
            <div className="space-y-3">{a.reviews.map((r) => (
              <div key={r.id} data-testid={`review-${r.id}`} className="rounded-xl border p-4 bg-card/60">
                <p className="text-sm text-amber-300">{"★".repeat(r.rating)}<span className="text-slate-600">{"★".repeat(5 - r.rating)}</span></p>
                <p className="text-sm mt-1">{r.comment}</p>
                <p className="text-xs text-muted-foreground mt-2">{r.customer_name} · {fmtDate(r.created_at)}</p>
              </div>))}
            </div>
          )}
        </div>
        {user?.role === "customer" && (
          <div className="flex gap-3">
            <ReportBlock targetId={a.id} trigger={<Button variant="ghost" size="sm" data-testid="report-astrologer"><Flag className="h-4 w-4 mr-2" />Report</Button>} mode="report" />
            <ReportBlock targetId={a.id} trigger={<Button variant="ghost" size="sm" data-testid="block-astrologer"><Ban className="h-4 w-4 mr-2" />Block</Button>} mode="block" />
          </div>
        )}
      </div>
      <aside className="glass rounded-2xl p-6 space-y-6 h-fit lg:sticky lg:top-24">
        <h2 className="text-xl">Book a consultation</h2>
        <Rates a={a} calls={calls} mode={mode} setMode={setMode} />
        {!calls.operational && <p data-testid="calls-not-operational" className="text-xs text-muted-foreground">Audio and video calls aren't available yet. Chat consultations are open.</p>}
        <Slots slots={a.slots} slot={slot} setSlot={setSlot} />
        {user?.role === "customer" && slot ? (
          <BookDialog a={a} slot={slot} mode={mode} policy={cfg.data.policy} onBooked={(b) => nav(`/bookings/${b.id}`)} />
        ) : (
          <Button data-testid="book-now-button" className="w-full rounded-full" onClick={startBooking}>{user ? "Choose a slot" : "Log in to book"}</Button>
        )}
        {!user && <p className="text-xs text-center text-muted-foreground">New here? <Link to="/register" className="text-amber-300">Create an account</Link></p>}
      </aside>
    </div>
  );
}
