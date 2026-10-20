import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "./ui/dialog";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { useAuth } from "../context/AuthContext";
import { errMsg } from "../lib/api";
import { haptic } from "../lib/native";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// compact login used in place, so the profile stays put behind it
export function LoginSheet({ open, onOpenChange, reason = "Log in to book a consultation", next }) {
  const { login } = useAuth();
  const [f, setF] = useState({ email: "", password: "" });
  const [touched, setTouched] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const errs = { email: !EMAIL.test(f.email.trim()) && "Enter a valid email address", password: f.password.length < 8 && "Password has at least 8 characters" };

  const submit = async (e) => {
    e.preventDefault();
    setTouched({ email: true, password: true });
    if (errs.email || errs.password || busy) return;
    setBusy(true);
    setError("");
    try {
      const u = await login(f.email.trim(), f.password);
      haptic("success");
      toast.success(`Welcome back, ${u.name.split(" ")[0]}`);
      onOpenChange(false);
    } catch (err) {
      haptic("error");
      setError(errMsg(err));
    } finally {
      setBusy(false);
    }
  };
  const field = (k, label, props) => (
    <div className="space-y-1.5">
      <Label htmlFor={`sheet-${k}`}>{label}</Label>
      <Input id={`sheet-${k}`} data-testid={`login-sheet-${k}`} value={f[k]} aria-invalid={!!(touched[k] && errs[k])}
        onChange={(e) => setF({ ...f, [k]: e.target.value })} onBlur={() => setTouched({ ...touched, [k]: true })} {...props} />
      {touched[k] && errs[k] && <p data-testid={`login-sheet-${k}-error`} className="text-[13px] text-red-300">{errs[k]}</p>}
    </div>
  );
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="login-sheet" className="bg-card sm:max-w-sm">
        <DialogHeader className="text-left pr-10">
          <DialogTitle className="font-serif text-xl">Log in</DialogTitle>
          <DialogDescription>{reason}</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} noValidate className="space-y-4">
          {field("email", "Email", { type: "email", inputMode: "email", autoComplete: "email", autoCapitalize: "none", enterKeyHint: "next" })}
          {field("password", "Password", { type: "password", autoComplete: "current-password", enterKeyHint: "go" })}
          {error && <p data-testid="login-sheet-error" role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-[13px] text-red-200">{error}</p>}
          <Button type="submit" data-testid="login-sheet-submit" disabled={busy} className="w-full rounded-full h-12 text-base">{busy ? "Logging in…" : "Log in"}</Button>
        </form>
        <p className="text-[13px] text-center text-muted-foreground">New here? <Link data-testid="login-sheet-register" to={`/register${next ? `?next=${encodeURIComponent(next)}` : ""}`} onClick={() => onOpenChange(false)} className="text-amber-300 py-2 inline-block">Create an account</Link></p>
      </DialogContent>
    </Dialog>
  );
}
