import { useEffect, useRef, useState } from "react";
import { Orbit, Send, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../../lib/api";
import { useLang } from "../../lib/i18n";

const TXT = {
  en: { title: "Astro AI", sub: "Ask about your chart. Answers come from your real planetary positions.", left: "questions left today", ph: "Ask about career, marriage, dasha...", none: "Today's 5 questions are used. Come back tomorrow.",
    chips: ["How will my career go in this dasha?", "What does my chart say about marriage?", "Which planet is strongest in my chart?"] },
  hi: { title: "एस्ट्रो AI", sub: "अपनी कुंडली के बारे में पूछें। जवाब आपकी असली ग्रह स्थिति से।", left: "सवाल आज बाकी", ph: "करियर, विवाह, दशा के बारे में पूछें...", none: "आज के 5 सवाल पूरे हो गए। कल फिर आएँ।",
    chips: ["इस दशा में मेरा करियर कैसा रहेगा?", "मेरी कुंडली विवाह के बारे में क्या कहती है?", "मेरी कुंडली में सबसे मज़बूत ग्रह कौन है?"] },
};

function Bubble({ m, i }) {
  const me = m.role === "user";
  return (
    <div data-testid={`astro-ai-msg-${i}`} className={`flex ${me ? "justify-end" : "justify-start"} gap-2`}>
      {!me && <span className="h-8 w-8 shrink-0 rounded-full border border-amber-400/50 bg-amber-400/10 grid place-items-center"><Orbit className="h-4 w-4 text-amber-300" /></span>}
      <p className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${me ? "bg-amber-400 text-[#0B1225] rounded-br-sm" : "border border-amber-400/25 bg-[#101a33] text-slate-100 rounded-bl-sm"}`}>{m.text}</p>
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
  const end = useRef(null);
  useEffect(() => { api.get(`/kundlis/${savedId}/chat`).then(({ data }) => { setMsgs(data.messages); setLeft(data.left); }).catch(() => {}); }, [savedId]);
  useEffect(() => { end.current?.scrollIntoView({ block: "nearest" }); }, [msgs, busy]);
  const send = async (text) => {
    const v = (text || q).trim();
    if (busy || v.length < 2 || left === 0) return;
    setBusy(true); setQ(""); setMsgs((x) => [...x, { role: "user", text: v }]);
    try { const { data } = await api.post(`/kundlis/${savedId}/chat`, { text: v, lang: lang === "hi" ? "hi" : "en" }, { timeout: 120000 }); setMsgs((x) => [...x, { role: "ai", text: data.reply }]); setLeft(data.left); }
    catch (e) { setMsgs((x) => x.slice(0, -1)); setQ(v); toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <section data-testid="astro-ai-chat" className="relative overflow-hidden rounded-2xl border border-amber-400/40 bg-gradient-to-b from-[#1b1630] to-[#0B1225]">
      <div className="flex items-center gap-3 border-b border-amber-400/20 px-4 sm:px-5 py-4">
        <span className="h-11 w-11 rounded-full border-2 border-amber-400/60 grid place-items-center bg-amber-400/10"><Orbit className="h-5 w-5 text-amber-300 animate-[spin_12s_linear_infinite]" /></span>
        <div className="flex-1 min-w-0"><p className="font-display text-lg text-amber-200 tracking-wide">{T.title}</p><p className="text-xs text-muted-foreground">{T.sub}</p></div>
        {left !== null && <span data-testid="astro-ai-left" className="shrink-0 rounded-full border border-amber-400/40 px-3 py-1 text-xs text-amber-200">{left}/5 {T.left}</span>}
      </div>
      <div className="max-h-[420px] overflow-y-auto px-4 sm:px-5 py-4 space-y-3">
        {msgs.length === 0 && <div className="flex flex-wrap gap-2">{T.chips.map((c, i) => <button key={c} type="button" data-testid={`astro-ai-chip-${i}`} onClick={() => send(c)} disabled={busy || left === 0} className="rounded-full border border-amber-400/30 bg-amber-400/5 px-3 py-2 text-xs text-amber-100 hover:bg-amber-400/15 min-h-9 text-left"><Sparkles className="inline h-3 w-3 mr-1 text-amber-300" />{c}</button>)}</div>}
        {msgs.map((m, i) => <Bubble key={i} m={m} i={i} />)}
        {busy && <div data-testid="astro-ai-typing" className="flex items-center gap-2 text-xs text-amber-200"><Loader2 className="h-4 w-4 animate-spin" />…</div>}
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
