import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Capacitor } from "@capacitor/core";
import { Preferences } from "@capacitor/preferences";
import { App as CapApp } from "@capacitor/app";

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

export function handleBack({ navigate, pathname }) {
  if (closeTopOverlay()) return "overlay";
  if ((window.history.state?.idx ?? 0) > 0) { navigate(-1); return "back"; }
  if (pathname !== "/") { navigate("/", { replace: true }); return "home"; }
  CapApp.minimizeApp();
  return "minimize";
}

// The only native listener registration in the app. The keyboard consumes Back before it reaches us.
export function NativeShell() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const ref = useRef({ navigate, pathname });
  ref.current = { navigate, pathname };
  useEffect(() => {
    if (!isNative) return undefined;
    let alive = true;
    const handles = [];
    const keep = (p) => p.then((h) => (alive ? handles.push(h) : h.remove()));
    keep(CapApp.addListener("backButton", () => handleBack(ref.current)));
    keep(CapApp.addListener("appStateChange", ({ isActive }) => { if (isActive) window.dispatchEvent(new Event("app:resume")); }));
    return () => { alive = false; handles.forEach((h) => h.remove()); };
  }, []);
  return null;
}
