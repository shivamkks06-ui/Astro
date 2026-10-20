import { useCallback, useEffect, useState } from "react";
import { api, errMsg } from "./api";

export function useApi(url) {
  const [state, setState] = useState({ data: null, loading: !!url, error: null });
  const load = useCallback(async (silent = false) => {
    if (!url) return;
    // background refreshes (resume/reconnect) keep the current screen instead of swapping in a spinner
    if (!silent) setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const { data } = await api.get(url);
      setState({ data, loading: false, error: null });
    } catch (e) {
      setState((s) => (silent && s.data ? s : { data: s.data, loading: false, error: errMsg(e) }));
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
