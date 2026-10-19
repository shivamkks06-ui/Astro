import { useState } from "react";
import { Mic, Camera, ShieldAlert, CheckCircle2 } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Button } from "./ui/button";
import { isNative } from "../lib/native";

// Explains why we need access before the OS prompt appears (Android shows its runtime dialog on getUserMedia).
export function MediaPermissionDialog({ open, onOpenChange, video, onGranted }) {
  const [state, setState] = useState("ask");
  const request = async () => {
    if (!navigator.mediaDevices?.getUserMedia) return setState("unsupported");
    setState("asking");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: !!video });
      stream.getTracks().forEach((t) => t.stop());
      setState("granted");
      onGranted?.();
    } catch (e) {
      setState(e?.name === "NotAllowedError" || e?.name === "SecurityError" ? "denied" : "error");
    }
  };
  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) setState("ask"); }}>
      <DialogContent data-testid="media-permission-dialog" className="bg-card">
        <DialogHeader>
          <DialogTitle className="font-serif">Allow {video ? "microphone and camera" : "microphone"}?</DialogTitle>
          <DialogDescription>We only use them during your live consultation, and calls are not recorded. You can withdraw access at any time in your device settings.</DialogDescription>
        </DialogHeader>
        <div className="flex gap-4 text-sm text-slate-300"><span className="flex items-center gap-2"><Mic className="h-4 w-4 text-amber-400" />Microphone</span>{video && <span className="flex items-center gap-2"><Camera className="h-4 w-4 text-amber-400" />Camera</span>}</div>
        {state === "granted" && <p data-testid="media-permission-granted" className="text-sm text-emerald-300 flex items-center gap-2"><CheckCircle2 className="h-4 w-4" />Access allowed.</p>}
        {state === "denied" && (
          <p data-testid="media-permission-denied" className="text-sm text-red-300 flex gap-2"><ShieldAlert className="h-4 w-4 shrink-0" />
            {isNative ? "Access was blocked. Open Settings › Apps › NakshatraVeda › Permissions and allow Microphone" + (video ? " and Camera" : "") + ", then try again." : "Access was blocked. Allow it from your browser's site settings, then try again."}
          </p>
        )}
        {state === "unsupported" && <p className="text-sm text-red-300">This device or browser doesn't support calls.</p>}
        {state === "error" && <p className="text-sm text-red-300">We couldn't reach your microphone{video ? " or camera" : ""}. Check that no other app is using it, then try again.</p>}
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Not now</Button>
          {state !== "granted" && <Button data-testid="media-permission-allow" disabled={state === "asking"} onClick={request}>{state === "asking" ? "Waiting…" : state === "denied" ? "Try again" : "Allow access"}</Button>}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
