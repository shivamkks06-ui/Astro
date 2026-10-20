import { useCallback, useEffect, useRef, useState } from "react";
import { api, errMsg } from "./api";

export function useApi(url) {
  const [state, setState] = useState({ data: null, loading: !!url, error: null });
  const latest = useRef(0);
  const load = useCallback(async (silent = false) => {
    if (!url) return;
    // only the newest request may update state: slow networks can return responses out of order
    const ticket = ++latest.current;
    // background refreshes (resume/reconnect) keep the current screen instead of swapping in a spinner
    if (!silent) setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const { data } = await api.get(url);
      if (ticket === latest.current) setState({ data, loading: false, error: null });
    } catch (e) {
      if (ticket === latest.current) setState((s) => (silent && s.data ? s : { data: s.data, loading: false, error: errMsg(e) }));
    }
  }, [url]);
  useEffect(() => {
    load();
    const again = () => load(true);
    window.addEventListener("app:reconnect", again);
    window.addEventListener("app:resume", again);
    return () => {
      window.removeEventListener("app:reconnect", again);
      window.removeEventListener("app:resume", again);
    };
  }, [load]);
  return { ...state, reload: () => load() };
}
