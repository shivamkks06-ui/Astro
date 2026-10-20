import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Capacitor } from "@capacitor/core";
import { Preferences } from "@capacitor/preferences";
import { App as CapApp } from "@capacitor/app";
import { Haptics, ImpactStyle, NotificationType } from "@capacitor/haptics";
import { toast } from "sonner";

// subtle confirmation feedback on key actions; silently no-op on web or unsupported devices
export function haptic(kind = "light") {
  if (!Capacitor.isNativePlatform()) return;
  const p = kind === "success" ? Haptics.notification({ type: NotificationType.Success })
    : kind === "error" ? Haptics.notification({ type: NotificationType.Error })
      : Haptics.impact({ style: ImpactStyle.Light });
  p.catch(() => {});
}

export const isNative = Capacitor.isNativePlatform();

// Native apps can't rely on cross-site cookies in the WebView, so they keep tokens in app storage.
let access = null;
export const tokens = {
  async load() {
    if (isNative) access = (await Preferences.get({ key: "access_token" })).value;
  },
  access: () => access,
  async refresh() {
    return isNative ? (await Preferences.get({ key: "refresh_token" })).value : null;
  },
  async save(data) {
    if (!isNative || !data) return;
    if (data.access_token) {
      access = data.access_token;
      await Preferences.set({ key: "access_token", value: access });
    }
    if (data.refresh_token) await Preferences.set({ key: "refresh_token", value: data.refresh_token });
  },
  async clear() {
    access = null;
    if (isNative) {
      await Preferences.remove({ key: "access_token" });
      await Preferences.remove({ key: "refresh_token" });
    }
  },
};

const OVERLAY = '[role="dialog"][data-state="open"],[role="alertdialog"][data-state="open"],[role="menu"][data-state="open"],[role="listbox"][data-state="open"]';

// Radix overlays close their topmost layer on Escape, so Back reuses that path instead of tracking overlays itself.
export function closeTopOverlay() {
  if (!document.querySelector(OVERLAY)) return false;
  (document.activeElement || document.body).dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", code: "Escape", keyCode: 27, bubbles: true, cancelable: true }));
  return true;
}

let exitArmedAt = 0;
const EXIT_WINDOW_MS = 2000;

export function handleBack({ navigate, pathname }) {
  if (closeTopOverlay()) return "overlay";
  if ((window.history.state?.idx ?? 0) > 0) { navigate(-1); return "back"; }
  if (pathname !== "/") { navigate("/", { replace: true }); return "home"; }
  // root screen: Android-style double press to exit
  if (Date.now() - exitArmedAt < EXIT_WINDOW_MS) {
    exitArmedAt = 0;
    toast.dismiss("exit-hint");
    if (Capacitor.isNativePlatform()) CapApp.exitApp();
    return "exit";
  }
  exitArmedAt = Date.now();
  toast("Press back again to exit", { id: "exit-hint", duration: EXIT_WINDOW_MS, position: "bottom-center" });
  return "exit-armed";
}

// The only native listener registration in the app. The keyboard consumes Back before it reaches us.
export function NativeShell() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const ref = useRef({ navigate, pathname });
  ref.current = { navigate, pathname };
  useEffect(() => {
    if (!isNative) {
      // dev-only hook so browser QA can drive the exact hardware-Back logic
      if (process.env.NODE_ENV !== "production") window.__nvBack = () => handleBack(ref.current);
      return undefined;
    }
    let alive = true;
    const handles = [];
    const keep = (p) => p.then((h) => (alive ? handles.push(h) : h.remove()));
    keep(CapApp.addListener("backButton", () => handleBack(ref.current)));
    keep(CapApp.addListener("appStateChange", ({ isActive }) => { if (isActive) window.dispatchEvent(new Event("app:resume")); }));
    return () => { alive = false; handles.forEach((h) => h.remove()); };
  }, []);
  return null;
}
