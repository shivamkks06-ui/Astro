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

export function initNativeShell() {
  if (!isNative) return () => {};
  const subs = [
    CapApp.addListener("backButton", ({ canGoBack }) => (canGoBack ? window.history.back() : CapApp.exitApp())),
    CapApp.addListener("appStateChange", ({ isActive }) => { if (isActive) window.dispatchEvent(new Event("app:resume")); }),
  ];
  return () => subs.forEach((s) => s.then((h) => h.remove()));
}
