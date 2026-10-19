import axios from "axios";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const api = axios.create({ baseURL: API, withCredentials: true, timeout: 30000 });

let refreshing = null;
const NO_REFRESH = ["/auth/login", "/auth/register", "/auth/refresh"];
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const cfg = err.config;
    if (err.response?.status === 401 && cfg && !cfg._retry && !NO_REFRESH.some((u) => cfg.url.includes(u))) {
      cfg._retry = true;
      refreshing = refreshing || api.post("/auth/refresh").finally(() => { refreshing = null; });
      try {
        await refreshing;
        return api(cfg);
      } catch (e) {
        return Promise.reject(err);
      }
    }
    return Promise.reject(err);
  }
);

export function errMsg(e) {
  if (!e?.response) return "Network problem. Check your connection and retry.";
  const d = e.response.data?.detail;
  if (d == null) return "Something went wrong. Please retry.";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => (x && typeof x.msg === "string" ? x.msg : JSON.stringify(x))).join(" ");
  if (typeof d.msg === "string") return d.msg;
  return String(d);
}

export const inr = (p) => { const v = p || 0; const f = v % 100 ? 2 : 0; return `${v < 0 ? "-" : ""}₹${(Math.abs(v) / 100).toLocaleString("en-IN", { minimumFractionDigits: f, maximumFractionDigits: 2 })}`; };
export const fmtDate = (d) => (d ? new Date(d).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "—");
export const idem = () => (window.crypto?.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);
export const label = (s) => (s || "").replace(/_/g, " ");
