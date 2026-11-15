import { useState } from "react";
import { Loader2 } from "lucide-react";
import { SocialLogin } from "@capgo/capacitor-social-login";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { useApi } from "../lib/useApi";
import { errMsg } from "../lib/api";
import { isNative } from "../lib/native";
import { useAuth } from "../context/AuthContext";

const G = () => (
  <svg viewBox="0 0 48 48" className="h-5 w-5" aria-hidden="true"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.8 1.1 7.9 3l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" /><path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3 0 5.8 1.1 7.9 3l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" /><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" /><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" /></svg>
);

let gisLoaded;
const loadGis = () => gisLoaded || (gisLoaded = new Promise((ok, bad) => {
  const s = document.createElement("script");
  s.src = "https://accounts.google.com/gsi/client";
  s.onload = ok; s.onerror = () => { gisLoaded = null; bad(new Error("Could not reach Google. Check your internet.")); };
  document.body.appendChild(s);
}));

// web: Google Identity Services popup; Android: native Google account picker. Both return an ID token verified by our backend.
async function getIdToken(clientId) {
  if (isNative) {
    await SocialLogin.initialize({ google: { webClientId: clientId } });
    const res = await SocialLogin.login({ provider: "google", options: {} });
    const tok = res?.result?.idToken;
    if (!tok) throw new Error("Google sign-in was cancelled.");
    return tok;
  }
  await loadGis();
  return new Promise((ok, bad) => {
    const client = window.google.accounts.id;
    client.initialize({ client_id: clientId, callback: (r) => (r.credential ? ok(r.credential) : bad(new Error("Google sign-in was cancelled."))), cancel_on_tap_outside: true });
    client.prompt((n) => { if (n.isNotDisplayed?.() || n.isSkippedMoment?.()) bad(new Error("Google sign-in was cancelled or blocked. Allow pop-ups and third-party sign-in, then try again.")); });
  });
}

export function GoogleButton({ role = "customer", acceptTerms = true, onDone, testid = "google-signin-button" }) {
  const cfg = useApi("/public/config");
  const { googleLogin } = useAuth();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [link, setLink] = useState(null);
  const [pw, setPw] = useState("");
  const clientId = cfg.data?.google_client_id;
  if (!clientId) return null;

  const send = async (id_token, password) => {
    try { onDone(await googleLogin({ id_token, role, accept_terms: acceptTerms, password })); }
    catch (e) {
      if (e?.response?.status === 409 && e.response.data?.detail === "link_required") { setLink(id_token); setErr(""); }
      else setErr(errMsg(e));
    }
  };
  const start = async () => {
    if (busy) return;
    setBusy(true); setErr("");
    try { await send(await getIdToken(clientId)); }
    catch (e) { setErr(/cancel/i.test(e?.message || "") ? "Google sign-in was cancelled." : errMsg(e)); }
    finally { setBusy(false); }
  };
  const confirmLink = async (e) => {
    e.preventDefault();
    if (!pw || busy) return;
    setBusy(true);
    await send(link, pw);
    setBusy(false);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 text-xs text-muted-foreground"><span className="h-px flex-1 bg-amber-400/20" />or<span className="h-px flex-1 bg-amber-400/20" /></div>
      {!link ? (
        <Button type="button" variant="outline" data-testid={testid} onClick={start} disabled={busy || !acceptTerms}
          className="w-full rounded-full h-12 text-base border-amber-400/40 bg-[#0B1225] hover:bg-amber-400/10 hover:text-amber-100">
          {busy ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <span className="mr-2"><G /></span>}Continue with Google
        </Button>
      ) : (
        <form onSubmit={confirmLink} data-testid="google-link-form" className="space-y-3 rounded-xl border border-amber-400/30 p-4">
          <p className="text-sm">An account with this email already exists. Enter its password once to link Google sign-in.</p>
          <Input type="password" data-testid="google-link-password" autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="Account password" />
          <div className="flex gap-2">
            <Button data-testid="google-link-submit" disabled={busy || !pw} className="rounded-full flex-1">{busy && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Link and log in</Button>
            <Button type="button" variant="ghost" data-testid="google-link-cancel" onClick={() => { setLink(null); setPw(""); }}>Cancel</Button>
          </div>
        </form>
      )}
      {err && <p data-testid="google-signin-error" role="alert" className="text-sm text-red-300">{err}</p>}
    </div>
  );
}
