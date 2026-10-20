import { useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Checkbox } from "../components/ui/checkbox";
import { errMsg } from "../lib/api";
import { useAuth, homeFor } from "../context/AuthContext";

const Shell = ({ title, sub, children }) => (
  <div className="max-w-md mx-auto px-4 py-16">
    <div className="glass gold-border rounded-2xl p-8 fade-up">
      <p className="overline mb-2">NakshatraVeda</p>
      <h1 className="text-3xl mb-2">{title}</h1>
      <p className="text-sm text-muted-foreground mb-8">{sub}</p>
      {children}
    </div>
  </div>
);

const Field = ({ id, label, ...p }) => (
  <div className="space-y-1.5"><Label htmlFor={id}>{label}</Label><Input id={id} data-testid={`${id}-input`} className="bg-background" {...p} /></div>
);

export function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [sp] = useSearchParams();
  const [f, setF] = useState({ email: "", password: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const u = await login(f.email, f.password);
      const next = sp.get("next");
      // came here from the page we return to: step back instead of stacking a duplicate entry
      if (next && loc.state?.from === next) nav(-1);
      else nav(next || homeFor(u), { replace: true });
    } catch (e2) { setErr(errMsg(e2)); } finally { setBusy(false); }
  };
  return (
    <Shell title="Welcome back" sub="Log in to manage your consultations.">
      <form onSubmit={submit} className="space-y-5">
        <Field id="login-email" label="Email" type="email" autoComplete="email" inputMode="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
        <Field id="login-password" label="Password" type="password" autoComplete="current-password" required value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
        {err && <p data-testid="login-error" className="text-sm text-red-400">{err}</p>}
        <Button data-testid="login-submit-button" className="w-full rounded-full" disabled={busy}>{busy ? "Logging in…" : "Log in"}</Button>
        <p className="text-sm text-center text-muted-foreground">No account? <Link to="/register" className="text-amber-300">Register</Link></p>
      </form>
    </Shell>
  );
}

export function RegisterPage() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [sp] = useSearchParams();
  const [f, setF] = useState({ name: "", email: "", password: "", role: sp.get("role") === "astrologer" ? "astrologer" : "customer", accept_terms: false });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try { const u = await register(f); nav(homeFor(u), { replace: true }); } catch (e2) { setErr(errMsg(e2)); } finally { setBusy(false); }
  };
  return (
    <Shell title="Create your account" sub="Choose how you'll use the platform.">
      <form onSubmit={submit} className="space-y-5">
        <div className="grid grid-cols-2 gap-3">
          {["customer", "astrologer"].map((r) => (
            <button type="button" key={r} data-testid={`register-role-${r}`} onClick={() => setF({ ...f, role: r })}
              className={`rounded-xl border p-3 text-sm capitalize transition-colors duration-200 ${f.role === r ? "border-amber-400 bg-amber-500/10" : ""}`}>
              {r === "customer" ? "I want a consultation" : "I am an astrologer"}
            </button>
          ))}
        </div>
        <Field id="register-name" label="Full name" required minLength={2} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
        <Field id="register-email" label="Email" type="email" autoComplete="email" inputMode="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
        <Field id="register-password" label="Password (min 8 characters)" type="password" autoComplete="new-password" required minLength={8} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
        <label className="flex gap-3 items-start text-xs text-muted-foreground">
          <Checkbox data-testid="register-accept-terms" checked={f.accept_terms} onCheckedChange={(v) => setF({ ...f, accept_terms: !!v })} />
          <span>I accept the <Link className="text-amber-300" to="/legal/terms">Terms</Link>, <Link className="text-amber-300" to="/legal/privacy">Privacy Policy</Link> and <Link className="text-amber-300" to="/legal/guidelines">Community Guidelines</Link>.</span>
        </label>
        {err && <p data-testid="register-error" className="text-sm text-red-400">{err}</p>}
        <Button data-testid="register-submit-button" className="w-full rounded-full" disabled={busy || !f.accept_terms}>{busy ? "Creating…" : "Create account"}</Button>
      </form>
    </Shell>
  );
}
