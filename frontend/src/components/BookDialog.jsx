import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "./ui/dialog";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Checkbox } from "./ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { toast } from "sonner";
import { api, errMsg, inr, fmtDate } from "../lib/api";
import { useApi } from "../lib/useApi";

const Row = ({ k, v, testid }) => (<div className="flex justify-between text-sm"><span className="text-muted-foreground">{k}</span><span data-testid={testid}>{v}</span></div>);

export function BookDialog({ a, slot, mode, policy, onBooked }) {
  const [open, setOpen] = useState(false);
  const [bp, setBp] = useState("none");
  const [note, setNote] = useState("");
  const [agree, setAgree] = useState(false);
  const [busy, setBusy] = useState(false);
  const profiles = useApi(open ? "/me/birth-profiles" : null);
  const total = a.rates[mode] * slot.duration_min;

  const submit = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/bookings", { slot_id: slot.id, mode, birth_profile_id: bp === "none" ? null : bp, note, accept_terms: agree });
      toast.success("Request sent. You'll pay once the astrologer accepts.");
      onBooked(data);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <Button data-testid="book-now-button" className="w-full rounded-full" onClick={() => setOpen(true)}>Review &amp; request booking</Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent data-testid="booking-dialog" className="bg-card max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="font-serif">Confirm consultation request</DialogTitle></DialogHeader>
          <div className="space-y-2 rounded-xl border p-4">
            <Row k="Astrologer" v={a.display_name} />
            <Row k="When" v={fmtDate(slot.start_at)} />
            <Row k="Mode" v={<span className="capitalize">{mode}</span>} />
            <Row k="Rate" v={`${inr(a.rates[mode])}/min × ${slot.duration_min} min`} />
            <Row k="Total (INR)" v={<b className="text-amber-300">{inr(total)}</b>} testid="booking-total" />
          </div>
          <div data-testid="refund-terms" className="text-xs text-muted-foreground space-y-1 leading-relaxed">
            <p>• You pay only after the astrologer accepts. The price is fixed now and won't change.</p>
            <p>• Cancel {policy.cancellation_window_hours}+ hours before the start: full refund. Later than that: {policy.late_cancel_refund_pct}% refund.</p>
            <p>• If the astrologer cancels or doesn't show up: full refund. If they end the session early, you get a pro-rata refund.</p>
            <p>• If you don't join a session the astrologer has started, the full amount is charged.</p>
            <p>• You can raise a dispute within {policy.dispute_window_hours} hours of completion.</p>
          </div>
          <Select value={bp} onValueChange={setBp}>
            <SelectTrigger data-testid="booking-birth-profile" className="bg-background"><SelectValue placeholder="Birth profile" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="none">Don't share a birth profile</SelectItem>
              {(profiles.data || []).map((p) => <SelectItem key={p.id} value={p.id}>{p.label}: {p.full_name}</SelectItem>)}
            </SelectContent>
          </Select>
          <Textarea data-testid="booking-note" maxLength={500} placeholder="What would you like guidance on? (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
          <label className="flex gap-3 items-start text-xs">
            <Checkbox data-testid="booking-accept-terms" checked={agree} onCheckedChange={(v) => setAgree(!!v)} />
            I understand the price and refund terms, and that astrology is interpretive guidance, not a guaranteed outcome or professional advice.
          </label>
          <DialogFooter>
            <Button data-testid="booking-submit" disabled={!agree || busy} onClick={submit}>{busy ? "Sending…" : "Send request"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
