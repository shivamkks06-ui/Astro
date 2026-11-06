import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Button } from "../components/ui/button";
import { api, errMsg } from "../lib/api";

const Card = ({ title, children }) => (
  <div className="max-w-md mx-auto px-5 py-12 sm:py-20">
    <div className="glass rounded-2xl p-6 sm:p-8 space-y-5">
      <h1 className="text-3xl">{title}</h1>
      {children}
    </div>
  </div>
);

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    if (busy) return;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) { setErr("Enter a valid email address."); return; }
    setBusy(true); setErr("");
    try { const { data } = await api.post("/auth/forgot-password", { email: email.trim() }); setMsg(data.message); }
    catch (e2) { setErr(errMsg(e2)); } finally { setBusy(false); }
  };
  return (
    <Card title="Forgot password">
      {msg ? <p data-testid="forgot-success" role="status" className="text-sm text-emerald-200">{msg} Check your inbox and spam folder.</p> : (
        <form onSubmit={submit} noValidate className="space-y-4">
          <p className="text-sm text-muted-foreground">Enter your account email and we'll send a secure link to set a new password.</p>
          <div className="space-y-1.5"><Label htmlFor="forgot-email">Email</Label>
            <Input id="forgot-email" data-testid="forgot-email-input" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
          {err && <p data-testid="forgot-error" role="alert" className="text-sm text-red-300">{err}</p>}
          <Button data-testid="forgot-submit" disabled={busy} className="w-full rounded-full h-12 font-semibold">{busy && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Send reset link</Button>
        </form>
      )}
      <Link to="/login" data-testid="forgot-back-login" className="block text-sm text-amber-200 underline underline-offset-4">Back to log in</Link>
    </Card>
  );
}

export function ResetPassword() {
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const token = sp.get("token") || "";
  const [pw, setPw] = useState({ a: "", b: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    if (busy) return;
    if (pw.a.length < 8) { setErr("Password must be at least 8 characters."); return; }
    if (pw.a !== pw.b) { setErr("The two passwords don't match."); return; }
    setBusy(true); setErr("");
    try { await api.post("/auth/reset-password", { token, password: pw.a }); nav("/login?reset=1", { replace: true }); }
    catch (e2) { setErr(errMsg(e2)); } finally { setBusy(false); }
  };
  if (!token) return <Card title="Reset password"><p data-testid="reset-missing" className="text-sm text-muted-foreground">This link is incomplete. <Link to="/forgot-password" className="text-amber-200 underline">Request a new one</Link>.</p></Card>;
  return (
    <Card title="Set a new password">
      <form onSubmit={submit} noValidate className="space-y-4">
        <div className="space-y-1.5"><Label htmlFor="reset-pw">New password</Label>
          <Input id="reset-pw" data-testid="reset-password-input" type="password" autoComplete="new-password" value={pw.a} onChange={(e) => setPw({ ...pw, a: e.target.value })} /></div>
        <div className="space-y-1.5"><Label htmlFor="reset-pw2">Confirm new password</Label>
          <Input id="reset-pw2" data-testid="reset-password-confirm" type="password" autoComplete="new-password" value={pw.b} onChange={(e) => setPw({ ...pw, b: e.target.value })} /></div>
        {err && <p data-testid="reset-error" role="alert" className="text-sm text-red-300">{err}</p>}
        <Button data-testid="reset-submit" disabled={busy} className="w-full rounded-full h-12 font-semibold">{busy && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Save new password</Button>
      </form>
    </Card>
  );
}
