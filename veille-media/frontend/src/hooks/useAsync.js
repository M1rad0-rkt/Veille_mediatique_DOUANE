import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "../services/api";

// Charge des données et expose { data, loading, error, reload }. Ignore les réponses obsolètes.
export default function useAsync(fn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const call = useRef(0);
  const run = useCallback(() => {
    const id = ++call.current;
    setState((s) => ({ ...s, loading: true, error: null }));
    fn().then(
      (data) => id === call.current && setState({ data, loading: false, error: null }),
      (e) => id === call.current && setState({ data: null, loading: false, error: errorMessage(e, "Chargement impossible") })
    );
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { run(); }, [run]);
  return { ...state, reload: run, setData: (data) => setState((s) => ({ ...s, data })) };
}
