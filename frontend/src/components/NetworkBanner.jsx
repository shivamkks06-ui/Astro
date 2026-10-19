import { useEffect, useState } from "react";
import { Network } from "@capacitor/network";
import { WifiOff, Wifi } from "lucide-react";

export function NetworkBanner() {
  const [online, setOnline] = useState(true);
  const [recovered, setRecovered] = useState(false);
  useEffect(() => {
    let prev = true;
    Network.getStatus().then((s) => { prev = s.connected; setOnline(s.connected); });
    const sub = Network.addListener("networkStatusChange", (s) => {
      setOnline(s.connected);
      if (s.connected && !prev) {
        setRecovered(true);
        window.dispatchEvent(new Event("app:reconnect"));
        setTimeout(() => setRecovered(false), 3000);
      }
      prev = s.connected;
    });
    return () => { sub.then((h) => h.remove()); };
  }, []);
  if (online && !recovered) return null;
  return (
    <div data-testid={online ? "network-restored-banner" : "offline-banner"} role="status"
      className={`sticky top-16 z-40 px-4 py-2 text-sm flex items-center justify-center gap-2 ${online ? "bg-emerald-600/90 text-white" : "bg-red-700/90 text-white"}`}>
      {online ? <><Wifi className="h-4 w-4" />Back online, refreshing…</> : <><WifiOff className="h-4 w-4" />You're offline. Changes can't be saved until you reconnect.</>}
    </div>
  );
}
