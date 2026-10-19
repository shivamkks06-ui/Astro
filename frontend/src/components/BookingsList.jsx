import { Link } from "react-router-dom";
import { Loading, ErrorState, Empty, StatusPill } from "./States";
import { useApi } from "../lib/useApi";
import { inr, fmtDate } from "../lib/api";

export function BookingsList({ role }) {
  const { data, loading, error, reload } = useApi("/me/bookings");
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!data.length) return <Empty title="No bookings yet" hint={role === "customer" ? "Find an astrologer to book your first consultation." : "Booking requests will show up here."} />;
  return (
    <div className="space-y-3" data-testid="bookings-list">
      {data.map((b) => (
        <Link key={b.id} to={`/bookings/${b.id}`} data-testid={`booking-row-${b.id}`} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 rounded-xl border p-4 bg-card/60 hover:border-amber-400/50 transition-colors duration-200">
          <div>
            <p className="font-medium">{role === "customer" ? b.astrologer_name : b.customer_name}</p>
            <p className="text-xs text-muted-foreground capitalize">{b.mode} · {fmtDate(b.slot_start)} · {b.booked_minutes} min</p>
          </div>
          <div className="flex items-center gap-3"><span className="text-sm">{inr(b.gross_paise)}</span><StatusPill status={b.status} /></div>
        </Link>
      ))}
    </div>
  );
}
