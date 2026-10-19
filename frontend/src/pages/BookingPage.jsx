import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Phone, Flag, Ban, Star } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Loading, ErrorState, StatusPill } from "../components/States";
import { ChatPanel } from "../components/ChatPanel";
import { BookingActions, Extensions } from "../components/BookingActions";
import { ReportBlock } from "../components/ReportBlock";
import { ActionDialog } from "../components/ActionDialog";
import { Disclaimer } from "../components/Layout";
import { MediaPermissionDialog } from "../components/MediaPermissionDialog";
import { useApi } from "../lib/useApi";
import { api, errMsg, inr, fmtDate } from "../lib/api";

const Row = ({ k, v, testid }) => <div className="flex justify-between gap-4 text-sm py-1"><span className="text-muted-foreground">{k}</span><span data-testid={testid} className="text-right">{v}</span></div>;

function Timer({ b }) {
  const [, tick] = useState(0);
  useEffect(() => { const t = setInterval(() => tick((x) => x + 1), 1000); return () => clearInterval(t); }, []);
  if (b.status !== "in_progress") return null;
  const offset = new Date(b.server_time) - b._fetchedAt;
  const end = new Date(b.started_at).getTime() + b.booked_minutes * 60000;
  const left = Math.max(0, Math.floor((end - (Date.now() + offset)) / 1000));
  return <p data-testid="session-timer" className="font-mono text-2xl text-amber-300">{String(Math.floor(left / 60)).padStart(2, "0")}:{String(left % 60).padStart(2, "0")} left</p>;
}

function Settlement({ s }) {
  if (!s) return null;
  return (
    <div className="rounded-xl border p-4" data-testid="settlement-summary">
      <p className="text-sm font-medium mb-2">Settlement</p>
      <Row k="Collected" v={inr(s.gross)} />
      <Row k="Refunded" v={inr(s.refund)} testid="settlement-refund" />
      <Row k="Charged" v={inr(s.retained)} />
      {s.refund_reason && <Row k="Refund reason" v={s.refund_reason.replace(/_/g, " ")} />}
    </div>
  );
}

function CallBox({ b }) {
  const [perm, setPerm] = useState(false);
  if (b.mode === "chat") return null;
  const requestToken = async () => { try { await api.post(`/bookings/${b.id}/call-token`); } catch (e) { toast.error(errMsg(e)); } };
  const tryCall = () => setPerm(true);
  return (
    <div className="rounded-xl border p-4 space-y-2" data-testid="call-box">
      <p className="text-sm">Before joining a call, you'll be asked to allow microphone{b.mode === "video" ? " and camera" : ""} access.</p>
      <Button data-testid="start-call-button" variant="outline" onClick={tryCall}><Phone className="h-4 w-4 mr-2" />Join {b.mode} call</Button>
      <p className="text-xs text-muted-foreground">Calling isn't live yet, and calls that don't connect are never charged.</p>
      <MediaPermissionDialog open={perm} onOpenChange={setPerm} video={b.mode === "video"} onGranted={() => { setPerm(false); requestToken(); }} />
    </div>
  );
}

export default function BookingPage() {
  const { id } = useParams();
  const { data, loading, error, reload } = useApi(`/bookings/${id}`);
  const [b, setB] = useState(null);
  useEffect(() => { if (data) setB({ ...data, _fetchedAt: Date.now() }); }, [data]);
  useEffect(() => {
    const t = setInterval(() => { if (b && !["completed", "cancelled", "expired"].includes(b.status)) reload(); }, 10000);
    return () => clearInterval(t);
  }, [b, reload]);
  useEffect(() => {
    if (b?.viewer_role === "customer" && b.status === "in_progress" && !b.customer_joined) { api.post(`/bookings/${b.id}/join`).catch(() => {}); }
  }, [b]);
  if (loading && !b) return <Loading />;
  if (error && !b) return <div className="max-w-3xl mx-auto px-4 py-16"><ErrorState error={error} onRetry={reload} /></div>;
  if (!b) return <Loading />;
  const other = b.viewer_role === "customer" ? b.astrologer_id : b.customer_id;
  const p = b.price;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-8 py-10 grid lg:grid-cols-[1fr_1.2fr] gap-8">
      <div className="space-y-6">
        <div>
          <p className="overline mb-2">Booking</p>
          <h1 className="text-2xl sm:text-3xl">{b.viewer_role === "customer" ? b.astrologer_name : b.customer_name}</h1>
          <div className="flex items-center gap-3 mt-3"><StatusPill status={b.status} testid="booking-status" /><span className="text-sm text-muted-foreground"><span className="capitalize">{b.mode}</span> · {fmtDate(b.slot_start)}</span></div>
        </div>
        <Timer b={b} />
        <BookingActions b={b} reload={reload} />
        <div className="rounded-xl border p-4">
          <p className="text-sm font-medium mb-2">Price fixed at booking</p>
          <Row k="Rate" v={`${inr(p.rate_paise_per_min)}/min`} />
          <Row k="Booked duration" v={`${b.booked_minutes} min`} />
          <Row k="Base price" v={inr(p.gross_paise)} testid="booking-price" />
          {(b.extensions || []).map((e) => <Row key={e.id} k={`Extension +${e.minutes}m`} v={inr(e.amount_paise)} />)}
          <Row k="Payments" v={b.payments.map((x) => `${inr(x.amount_paise)} ${x.status}`).join(", ") || "—"} />
        </div>
        <Settlement s={b.settlement} />
        <Extensions b={b} reload={reload} />
        <CallBox b={b} />
        {b.birth_details && (
          <div className="rounded-xl border p-4" data-testid="birth-details">
            <p className="text-sm font-medium mb-2">Birth details shared</p>
            <Row k="Name" v={b.birth_details.full_name} /><Row k="Date" v={b.birth_details.birth_date} /><Row k="Time" v={b.birth_details.birth_time || "Unknown"} /><Row k="Place" v={b.birth_details.birth_place} />
          </div>
        )}
        {b.note && <p className="text-sm text-muted-foreground">Note: {b.note}</p>}
        {b.viewer_role === "customer" && b.status === "completed" && !b.has_review && b.customer_joined && (
          <ActionDialog testid="leave-review" trigger={<Button variant="outline"><Star className="h-4 w-4 mr-2" />Leave a review</Button>} title="Review this consultation"
            fields={[{ name: "rating", label: "Rating", type: "select", options: ["5", "4", "3", "2", "1"] }, { name: "comment", label: "Comment", type: "textarea" }]}
            onSubmit={(v) => api.post(`/bookings/${b.id}/review`, { rating: Number(v.rating || 5), comment: v.comment || "" }).then(reload)} />
        )}
        {b.viewer_role !== "admin" && (
          <div className="flex gap-2">
            <ReportBlock targetId={other} bookingId={b.id} mode="report" trigger={<Button variant="ghost" size="sm" data-testid="booking-report"><Flag className="h-4 w-4 mr-2" />Report</Button>} />
            <ReportBlock targetId={other} mode="block" trigger={<Button variant="ghost" size="sm" data-testid="booking-block"><Ban className="h-4 w-4 mr-2" />Block</Button>} />
          </div>
        )}
        <Disclaimer />
      </div>
      <ChatPanel booking={b} canSend={b.status === "in_progress" && b.viewer_role !== "admin"} />
    </div>
  );
}
