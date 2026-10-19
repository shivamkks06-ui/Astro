import { useState } from "react";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";
import { api, errMsg } from "../../lib/api";

const Chips = ({ items, value, onChange, testid }) => (
  <div className="flex flex-wrap gap-2">
    {items.map((i) => {
      const on = value.includes(i);
      return (
        <button type="button" key={i} data-testid={`${testid}-${i.replace(/\s/g, "-").toLowerCase()}`} onClick={() => onChange(on ? value.filter((x) => x !== i) : [...value, i])}
          className={`rounded-full border px-3 py-1 text-xs transition-colors duration-200 ${on ? "border-amber-400 bg-amber-500/15 text-amber-200" : "hover:border-amber-400/50"}`}>{i}</button>
      );
    })}
  </div>
);

export function ProfileForm({ profile, cfg, calls, reload }) {
  const [f, setF] = useState({
    display_name: profile.display_name, bio: profile.bio, languages: profile.languages, expertise: profile.expertise,
    experience_years: profile.experience_years, credential_summary: profile.credential_summary || "", modes_enabled: profile.modes_enabled,
    rates: { chat: profile.rates.chat / 100, audio: profile.rates.audio / 100, video: profile.rates.video / 100 },
    payout_account: profile.payout_account || { beneficiary_name: "", method: "upi", upi_id: "", account_last4: "", ifsc: "" },
  });
  const [busy, setBusy] = useState(false);
  const pa = f.payout_account;
  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payout = pa.beneficiary_name ? { beneficiary_name: pa.beneficiary_name, method: pa.method, upi_id: pa.method === "upi" ? pa.upi_id : null, account_last4: pa.method === "bank" ? pa.account_last4 : null, ifsc: pa.method === "bank" ? pa.ifsc : null } : null;
      await api.put("/astrologer/profile", {
        ...f, experience_years: Number(f.experience_years), payout_account: payout,
        rates: Object.fromEntries(Object.entries(f.rates).map(([k, v]) => [k, Math.round(Number(v || 0) * 100)])),
      });
      toast.success("Profile saved");
      reload();
    } catch (e2) { toast.error(errMsg(e2)); } finally { setBusy(false); }
  };
  return (
    <form onSubmit={save} className="grid lg:grid-cols-2 gap-8" data-testid="astro-profile-form">
      <div className="space-y-4">
        <div className="space-y-1.5"><Label>Display name</Label><Input data-testid="astro-display-name" value={f.display_name} onChange={(e) => setF({ ...f, display_name: e.target.value })} className="bg-background" /></div>
        <div className="space-y-1.5"><Label>About you</Label><Textarea data-testid="astro-bio" rows={6} maxLength={2000} value={f.bio} onChange={(e) => setF({ ...f, bio: e.target.value })} placeholder="Your approach and background. Don't promise outcomes." /></div>
        <div className="space-y-1.5"><Label>Years of experience</Label><Input data-testid="astro-experience" type="number" min="0" max="70" value={f.experience_years} onChange={(e) => setF({ ...f, experience_years: e.target.value })} className="bg-background" /></div>
        <div className="space-y-1.5"><Label>Stated qualifications (shown as "not yet reviewed" until credentials are approved)</Label><Input data-testid="astro-credential-summary" maxLength={300} value={f.credential_summary} onChange={(e) => setF({ ...f, credential_summary: e.target.value })} className="bg-background" /></div>
        <div className="space-y-2"><Label>Languages</Label><Chips testid="astro-lang" items={cfg.languages} value={f.languages} onChange={(v) => setF({ ...f, languages: v })} /></div>
        <div className="space-y-2"><Label>Expertise</Label><Chips testid="astro-exp" items={cfg.expertise} value={f.expertise} onChange={(v) => setF({ ...f, expertise: v })} /></div>
      </div>
      <div className="space-y-6">
        <div className="rounded-xl border p-4 space-y-3">
          <p className="text-sm font-medium">Consultation modes &amp; rates (₹ per minute)</p>
          {["chat", "audio", "video"].map((m) => (
            <div key={m} className="flex items-center gap-3">
              <input type="checkbox" data-testid={`astro-mode-${m}`} className="accent-amber-400" checked={f.modes_enabled.includes(m)}
                onChange={(e) => setF({ ...f, modes_enabled: e.target.checked ? [...f.modes_enabled, m] : f.modes_enabled.filter((x) => x !== m) })} />
              <span className="capitalize w-14 text-sm">{m}</span>
              <Input data-testid={`astro-rate-${m}`} type="number" min="0" step="0.5" value={f.rates[m]} onChange={(e) => setF({ ...f, rates: { ...f.rates, [m]: e.target.value } })} className="bg-background w-32" />
            </div>
          ))}
          {!calls.operational && <p className="text-xs text-muted-foreground">Customers can't book audio/video yet because calling isn't live.</p>}
        </div>
        <div className="rounded-xl border p-4 space-y-3">
          <p className="text-sm font-medium">Payout account</p>
          <p className="text-xs text-muted-foreground">We only keep a reference: a UPI ID, or the last 4 digits and IFSC of a bank account. Never share PINs or passwords.</p>
          <Input data-testid="payout-beneficiary" placeholder="Beneficiary name" value={pa.beneficiary_name} onChange={(e) => setF({ ...f, payout_account: { ...pa, beneficiary_name: e.target.value } })} className="bg-background" />
          <select data-testid="payout-method" value={pa.method} onChange={(e) => setF({ ...f, payout_account: { ...pa, method: e.target.value } })} className="w-full h-10 rounded-md border bg-background px-3 text-sm">
            <option value="upi">UPI</option><option value="bank">Bank account</option>
          </select>
          {pa.method === "upi" ? (
            <Input data-testid="payout-upi" placeholder="name@bank" value={pa.upi_id || ""} onChange={(e) => setF({ ...f, payout_account: { ...pa, upi_id: e.target.value } })} className="bg-background" />
          ) : (
            <div className="grid grid-cols-2 gap-2">
              <Input data-testid="payout-last4" placeholder="Last 4 digits" maxLength={4} value={pa.account_last4 || ""} onChange={(e) => setF({ ...f, payout_account: { ...pa, account_last4: e.target.value } })} className="bg-background" />
              <Input data-testid="payout-ifsc" placeholder="IFSC" value={pa.ifsc || ""} onChange={(e) => setF({ ...f, payout_account: { ...pa, ifsc: e.target.value.toUpperCase() } })} className="bg-background" />
            </div>
          )}
        </div>
        <Button data-testid="astro-profile-save" disabled={busy} className="rounded-full">{busy ? "Saving…" : "Save profile"}</Button>
      </div>
    </form>
  );
}
