import axios from "axios";
import { isNative, tokens } from "./native";

const BACKEND = process.env.REACT_APP_BACKEND_URL;
export const BACKEND_MISSING = !BACKEND || BACKEND === "undefined";
export const API = `${BACKEND}/api`;
export const api = axios.create({ baseURL: API, withCredentials: true, timeout: 30000 });

api.interceptors.request.use((cfg) => {
  if (BACKEND_MISSING) throw new Error("App is not configured: REACT_APP_BACKEND_URL was missing when this build was made.");
  if (isNative) {
    cfg.headers["X-Client"] = "native";
    if (tokens.access()) cfg.headers.Authorization = `Bearer ${tokens.access()}`;
  }
  return cfg;
});

const doRefresh = async () => {
  const { data } = await api.post("/auth/refresh", isNative ? { refresh_token: await tokens.refresh() } : {});
  await tokens.save(data);
  return data;
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let refreshing = null;
const NO_REFRESH = ["/auth/login", "/auth/register", "/auth/refresh"];
api.interceptors.response.use(
  (r) => {
    // an HTML page instead of JSON means the request never reached the API server
    if (typeof r.data === "string" && /^\s*</.test(r.data)) {
      return Promise.reject(Object.assign(new Error("Could not reach the NakshatraVeda server (got a web page instead of data). Check the backend URL in this build."), { config: r.config }));
    }
    return r;
  },
  async (err) => {
    const cfg = err.config;
    // flaky mobile networks: retry idempotent GETs with backoff
    if (!err.response && err.code === "ERR_NETWORK" && cfg && cfg.method === "get" && (cfg._netRetry || 0) < 2) {
      cfg._netRetry = (cfg._netRetry || 0) + 1;
      await sleep(800 * 2 ** cfg._netRetry);
      return api(cfg);
    }
    if (err.response?.status === 401 && cfg && !cfg._retry && !NO_REFRESH.some((u) => cfg.url.includes(u))) {
      cfg._retry = true;
      refreshing = refreshing || doRefresh().finally(() => { refreshing = null; });
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
  if (!e?.response) return e?.code === "ERR_NETWORK" || !e?.message ? "Network problem. Check your connection and retry." : e.message;
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
