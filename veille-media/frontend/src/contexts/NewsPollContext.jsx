// Actualisation automatique : interroge /news/latest toutes les 30 s et signale les nouvelles actualités.
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { news } from "../services/endpoints";

const PollContext = createContext({ newCount: 0, refreshKey: 0, acknowledge: () => {} });
const INTERVAL_MS = 30_000;

export function NewsPollProvider({ children }) {
  const [newCount, setNewCount] = useState(0);
  const [refreshKey, setRefreshKey] = useState(0);
  const since = useRef(null);

  useEffect(() => {
    let stopped = false;
    const tick = async () => {
      if (document.hidden) return;                      // onglet en arrière-plan : on économise les requêtes
      try {
        const d = await news.latest(since.current);
        if (stopped) return;
        if (since.current !== null && d.count > 0) setNewCount((c) => c + d.count);
        since.current = d.server_time;                  // la 1re réponse sert seulement de point de départ
      } catch { /* réseau coupé : on réessaie au prochain tour */ }
    };
    tick();
    const id = setInterval(tick, INTERVAL_MS);
    return () => { stopped = true; clearInterval(id); };
  }, []);

  const acknowledge = useCallback(() => { setNewCount(0); setRefreshKey((k) => k + 1); }, []);
  return <PollContext.Provider value={{ newCount, refreshKey, acknowledge }}>{children}</PollContext.Provider>;
}

export const useNewsPoll = () => useContext(PollContext);
