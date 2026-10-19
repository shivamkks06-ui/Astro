import { useCallback, useEffect, useRef, useState } from "react";
import { Send, RotateCw, AlertCircle } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { api, errMsg, idem } from "../lib/api";

export function ChatPanel({ booking, canSend }) {
  const [msgs, setMsgs] = useState([]);
  const [text, setText] = useState("");
  const [netErr, setNetErr] = useState("");
  const last = useRef(null);
  const box = useRef(null);
  const me = booking.viewer_role;

  const poll = useCallback(async () => {
    try {
      const q = last.current ? `?after=${encodeURIComponent(last.current)}` : "";
      const { data } = await api.get(`/bookings/${booking.id}/messages${q}`);
      setNetErr("");
      if (data.length) {
        last.current = data[data.length - 1].created_at;
        setMsgs((m) => {
          const known = new Set(m.map((x) => x.client_msg_id));
          return [...m.map((x) => (data.find((d) => d.client_msg_id === x.client_msg_id) ? { ...x, state: "sent" } : x)), ...data.filter((d) => !known.has(d.client_msg_id))];
        });
      }
    } catch (e) { setNetErr(errMsg(e)); }
  }, [booking.id]);

  useEffect(() => {
    poll();
    const t = setInterval(poll, 3000);
    return () => clearInterval(t);
  }, [poll]);
  useEffect(() => { box.current?.scrollTo(0, box.current.scrollHeight); }, [msgs.length]);

  const send = async (msg) => {
    setMsgs((m) => (m.find((x) => x.client_msg_id === msg.client_msg_id) ? m.map((x) => (x.client_msg_id === msg.client_msg_id ? { ...x, state: "sending" } : x)) : [...m, { ...msg, state: "sending" }]));
    try {
      await api.post(`/bookings/${booking.id}/messages`, { client_msg_id: msg.client_msg_id, text: msg.text });
      setMsgs((m) => m.map((x) => (x.client_msg_id === msg.client_msg_id ? { ...x, state: "sent" } : x)));
    } catch (e) {
      setMsgs((m) => m.map((x) => (x.client_msg_id === msg.client_msg_id ? { ...x, state: "failed", err: errMsg(e) } : x)));
    }
  };
  const submit = (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    send({ client_msg_id: idem(), text: text.trim(), sender_role: me, created_at: new Date().toISOString() });
    setText("");
  };

  return (
    <div className="glass rounded-2xl flex flex-col h-[460px]" data-testid="chat-panel">
      <div className="px-5 py-3 border-b text-sm flex justify-between"><span className="font-serif">Consultation chat</span>{netErr && <span data-testid="chat-network-error" className="text-xs text-red-300">Reconnecting…</span>}</div>
      <div ref={box} className="flex-1 overflow-y-auto p-5 space-y-3" data-testid="chat-messages">
        {msgs.length === 0 && <p className="text-sm text-muted-foreground text-center mt-12">No messages yet.</p>}
        {msgs.map((m) => (
          <div key={m.client_msg_id} className={`flex ${m.sender_role === me ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${m.sender_role === me ? "bg-amber-500/20 text-amber-50" : "bg-secondary"}`}>
              <p className="whitespace-pre-wrap break-words">{m.text}</p>
              <p className="text-[10px] text-muted-foreground mt-1 flex items-center gap-1">
                {new Date(m.created_at).toLocaleTimeString("en-IN", { timeStyle: "short" })}
                {m.state === "sending" && " · sending"}
                {m.state === "failed" && (
                  <button data-testid="chat-retry" onClick={() => send(m)} className="text-red-300 flex items-center gap-1"><AlertCircle className="h-3 w-3" />{m.err} <RotateCw className="h-3 w-3" /></button>
                )}
              </p>
            </div>
          </div>
        ))}
      </div>
      {canSend ? (
        <form onSubmit={submit} className="p-3 border-t flex gap-2">
          <Input data-testid="chat-input" maxLength={2000} value={text} onChange={(e) => setText(e.target.value)} placeholder="Type a message" className="bg-background" />
          <Button data-testid="chat-send-button" size="icon"><Send className="h-4 w-4" /></Button>
        </form>
      ) : <p className="p-3 border-t text-xs text-center text-muted-foreground">You can only send messages during a live session.</p>}
    </div>
  );
}
