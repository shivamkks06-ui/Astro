import { useCallback, useEffect, useRef, useState } from "react";
import { Orbit, Send, Sparkles, Volume2, Square } from "lucide-react";
import { TextToSpeech } from "@capacitor-community/text-to-speech";
import { isNative } from "../../lib/native";
import { toast } from "sonner";
import { api, errMsg } from "../../lib/api";
import { useLang } from "../../lib/i18n";

const TXT = {
  en: { title: "Astro AI", sub: "Ask about your chart. Answers come from your real planetary positions.", left: "questions left today", ph: "Ask about career, marriage, dasha...", none: "Today's 5 questions are used. Come back tomorrow.",
    chips: ["How will my career go in this dasha?", "What does my chart say about marriage?", "Which planet is strongest in my chart?"] },
  hi: { title: "एस्ट्रो AI", sub: "अपनी कुंडली के बारे में पूछें। जवाब आपकी असली ग्रह स्थिति से।", left: "सवाल आज बाकी", ph: "करियर, विवाह, दशा के बारे में पूछें...", none: "आज के 5 सवाल पूरे हो गए। कल फिर आएँ।",
    chips: ["इस दशा में मेरा करियर कैसा रहेगा?", "मेरी कुंडली विवाह के बारे में क्या कहती है?", "मेरी कुंडली में सबसे मज़बूत ग्रह कौन है?"] },
};

function Typer({ text, onTick }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (n >= text.length) return undefined;
    const id = setTimeout(() => { setN((x) => Math.min(text.length, x + 3)); onTick?.(); }, 18);
    return () => clearTimeout(id);
  }, [n, text, onTick]);
  return <>{text.slice(0, n)}{n < text.length && <span className="ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 bg-amber-300 animate-pulse" />}</>;
}

function Avatar({ size = "h-8 w-8", icon = "h-4 w-4", live }) {
  return (
    <span className={`astro-orb relative ${size} shrink-0 rounded-full grid place-items-center ${live ? "astro-orb-live" : ""}`}>
      <Orbit className={`${icon} text-amber-200 animate-[spin_8s_linear_infinite]`} />
    </span>
  );
}

const isHi = (s) => /[\u0900-\u097F]/.test(s);
const stopVoice = () => { if (isNative) TextToSpeech.stop().catch(() => {}); else window.speechSynthesis?.cancel(); };
async function speak(text, onEnd) {
  const lang = isHi(text) ? "hi-IN" : "en-IN";
  if (isNative) { await TextToSpeech.speak({ text, lang, rate: 0.95 }); onEnd(); return; }
  const s = window.speechSynthesis;
  if (!s) throw new Error("no-voice");
  s.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang; u.rate = 0.95;
  u.voice = s.getVoices().find((v) => v.lang === lang) || s.getVoices().find((v) => v.lang.startsWith(lang.slice(0, 2))) || null;
  u.onend = onEnd; u.onerror = onEnd;
  s.speak(u);
}

function SpeakBtn({ text, i, playing, setPlaying }) {
  const on = playing === i;
  const click = async () => {
    stopVoice();
    if (on) { setPlaying(null); return; }
    setPlaying(i);
    try { await speak(text, () => setPlaying((p) => (p === i ? null : p))); }
    catch { setPlaying(null); toast.error(isHi(text) ? "इस डिवाइस पर आवाज़ उपलब्ध नहीं है।" : "Voice is not available on this device."); }
  };
  return (
    <button type="button" data-testid={`astro-ai-speak-${i}`} onClick={click} aria-label={on ? "Stop" : "Listen"}
      className={`mt-1 inline-flex items-center gap-1.5 rounded-full border px-3 min-h-9 text-xs transition-colors ${on ? "border-amber-300 bg-amber-400/20 text-amber-100" : "border-amber-400/30 text-amber-300 hover:bg-amber-400/10"}`}>
      {on ? <><Square className="h-3 w-3 fill-current" /><span className="flex items-end gap-0.5 h-3">{[0, 1, 2, 3].map((d) => <span key={d} className="astro-bar w-0.5 bg-amber-200" style={{ animationDelay: `${d * 0.12}s` }} />)}</span></> : <Volume2 className="h-3.5 w-3.5" />}
      {on ? (isHi(text) ? "रोकें" : "Stop") : (isHi(text) ? "सुनें" : "Listen")}
    </button>
  );
}

function Bubble({ m, i, onTick, playing, setPlaying }) {
  const me = m.role === "user";
  return (
    <div data-testid={`astro-ai-msg-${i}`} className={`astro-pop flex ${me ? "justify-end" : "justify-start"} gap-2`}>
      {!me && <Avatar />}
      <div className={`max-w-[85%] ${me ? "" : "flex flex-col items-start"}`}>
        <p className={`whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${me ? "bg-amber-400 text-[#0B1225] rounded-br-sm" : "border border-amber-400/25 bg-[#101a33] text-slate-100 rounded-bl-sm"}`}>{m.fresh ? <Typer text={m.text} onTick={onTick} /> : m.text}</p>
        {!me && <SpeakBtn text={m.text} i={i} playing={playing} setPlaying={setPlaying} />}
      </div>
    </div>
  );
}

export function AstroChat({ savedId }) {
  const { lang } = useLang();
  const T = TXT[lang === "hi" ? "hi" : "en"];
  const [msgs, setMsgs] = useState([]);
  const [left, setLeft] = useState(null);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(null);
  useEffect(() => stopVoice, []);
  const end = useRef(null);
  useEffect(() => { api.get(`/kundlis/${savedId}/chat`).then(({ data }) => { setMsgs(data.messages); setLeft(data.left); }).catch(() => {}); }, [savedId]);
  const tick = useCallback(() => { end.current?.scrollIntoView({ block: "nearest" }); }, []);
  useEffect(() => { tick(); }, [msgs, busy, tick]);
  const send = async (text) => {
    const v = (text || q).trim();
    if (busy || v.length < 2 || left === 0) return;
    setBusy(true); setQ(""); setMsgs((x) => [...x, { role: "user", text: v }]);
    try { const { data } = await api.post(`/kundlis/${savedId}/chat`, { text: v, lang: lang === "hi" ? "hi" : "en" }, { timeout: 120000 }); setMsgs((x) => [...x, { role: "ai", text: data.reply, fresh: true }]); setLeft(data.left); }
    catch (e) { setMsgs((x) => x.slice(0, -1)); setQ(v); toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <section data-testid="astro-ai-chat" className="relative overflow-hidden rounded-2xl border border-amber-400/40 bg-gradient-to-b from-[#1b1630] to-[#0B1225]">
      <div className="flex flex-wrap items-center gap-3 border-b border-amber-400/20 px-4 sm:px-5 py-4">
        <Avatar size="h-12 w-12" icon="h-6 w-6" live={busy} />
        <div className="flex-1 min-w-[180px]"><p className="font-display text-lg text-amber-200 tracking-wide">{T.title}</p><p className="text-xs text-muted-foreground">{T.sub}</p></div>
        {left !== null && <span data-testid="astro-ai-left" className="shrink-0 ml-[60px] sm:ml-0 rounded-full border border-amber-400/40 px-3 py-1 text-xs text-amber-200">{left}/5 {T.left}</span>}
      </div>
      <div className="max-h-[420px] overflow-y-auto px-4 sm:px-5 py-4 space-y-3">
        {msgs.length === 0 && <div className="flex flex-wrap gap-2">{T.chips.map((c, i) => <button key={c} type="button" data-testid={`astro-ai-chip-${i}`} onClick={() => send(c)} disabled={busy || left === 0} className="rounded-full border border-amber-400/30 bg-amber-400/5 px-3 py-2 text-xs text-amber-100 hover:bg-amber-400/15 min-h-9 text-left"><Sparkles className="inline h-3 w-3 mr-1 text-amber-300" />{c}</button>)}</div>}
        {msgs.map((m, i) => <Bubble key={i} m={m} i={i} onTick={tick} playing={playing} setPlaying={setPlaying} />)}
        {busy && <div data-testid="astro-ai-typing" className="astro-pop flex items-center gap-2"><Avatar live /><span className="flex gap-1 rounded-2xl rounded-bl-sm border border-amber-400/25 bg-[#101a33] px-4 py-3">{[0, 1, 2].map((d) => <span key={d} className="astro-dot h-2 w-2 rounded-full bg-amber-300" style={{ animationDelay: `${d * 0.18}s` }} />)}</span></div>}
        <div ref={end} />
      </div>
      {left === 0 ? <p data-testid="astro-ai-limit" className="border-t border-amber-400/20 px-5 py-4 text-sm text-amber-100">{T.none}</p> : (
        <form onSubmit={(e) => { e.preventDefault(); send(); }} className="flex gap-2 border-t border-amber-400/20 p-3">
          <input data-testid="astro-ai-input" value={q} onChange={(e) => setQ(e.target.value)} maxLength={500} placeholder={T.ph} className="flex-1 min-w-0 h-11 rounded-full border border-input bg-[#0E1830] px-4 text-sm" />
          <button type="submit" data-testid="astro-ai-send" disabled={busy || q.trim().length < 2} aria-label="Send" className="h-11 w-11 shrink-0 rounded-full bg-amber-400 text-[#0B1225] grid place-items-center disabled:opacity-50"><Send className="h-4 w-4" /></button>
        </form>
      )}
      <p className="px-5 pb-3 text-[10px] text-muted-foreground">AI interpretation, guidance only.</p>
    </section>
  );
}
