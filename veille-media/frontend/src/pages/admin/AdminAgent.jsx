import { useEffect, useState } from "react";
import { Play, Sparkles } from "lucide-react";
import { ErrorBox, Loading, PageTitle, StatusBadge } from "../../components/ui";
import useAsync from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { admin, agent } from "../../services/endpoints";
import { formatDateTime, timeAgo } from "../../utils/format";

export default function AdminAgent() {
  const status = useAsync(() => agent.status(), []);
  const logs = useAsync(() => agent.logs({ page_size: 30 }), []);
  const settings = useAsync(() => admin.settings(), []);
  const [interval, setInterval_] = useState("");
  const [applyAll, setApplyAll] = useState(false);
  const [msg, setMsg] = useState("");

  // Rafraîchissement automatique toutes les 10 s : l'état de l'agent se suit en direct.
  useEffect(() => {
    const id = window.setInterval(() => { status.reload(); logs.reload(); }, 10_000);
    return () => window.clearInterval(id);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (settings.data) setInterval_(String(settings.data.default_interval_minutes)); }, [settings.data]);

  if ((status.loading && !status.data) || (logs.loading && !logs.data)) return <Loading />;
  if (status.error) return <ErrorBox message={status.error} onRetry={status.reload} />;
  const s = status.data;
  const run = async (fn, ok) => { try { await fn(); setMsg(ok); status.reload(); } catch (e) { setMsg(errorMessage(e)); } };
  const saveInterval = async () => {
    try { await admin.saveSettings({ default_interval_minutes: Number(interval), apply_to_all_sources: applyAll }); setMsg("Fréquence enregistrée"); status.reload(); }
    catch (e) { setMsg(errorMessage(e)); }
  };

  return (
    <>
      <PageTitle title="Agent de collecte" subtitle="État du worker, des sources et du traitement IA"
        actions={<>
          <button className="btn-primary" onClick={() => run(() => agent.collect(null), "Collecte demandée pour toutes les sources actives")}><Play className="h-4 w-4" /> Collecter maintenant</button>
          <button className="btn-outline" disabled={!s.ai.configured} onClick={() => run(() => agent.process(), "Traitement IA demandé")}><Sparkles className="h-4 w-4" /> Lancer le traitement IA</button>
        </>} />
      {msg && <p role="status" className="mb-3 text-sm text-slate-600 dark:text-slate-300">{msg}</p>}

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <div className="card p-4"><p className="text-xs text-slate-500">Worker</p>
          <p className={`mt-1 font-semibold ${s.worker_alive ? "text-emerald-600" : "text-red-600"}`}>{s.worker_alive ? "En marche" : "Arrêté ou injoignable"}</p>
          <p className="text-xs text-slate-400">Dernier signal : {timeAgo(s.worker_last_seen)}</p></div>
        <div className="card p-4"><p className="text-xs text-slate-500">Intelligence artificielle</p>
          <p className={`mt-1 font-semibold ${s.ai.configured ? "" : "text-amber-600"}`}>{s.ai.configured ? `${s.ai.provider} · ${s.ai.model}` : "Non configurée"}</p>
          <p className="text-xs text-slate-400">{s.ai.configured ? `${s.pending_ai} article(s) en attente` : "Renseignez GEMINI_API_KEY dans .env puis redémarrez"}</p></div>
        <div className="card p-4"><p className="text-xs text-slate-500">Fréquence de collecte par défaut</p>
          <div className="mt-1 flex items-center gap-2">
            <input className="input !w-20 !py-1" type="number" min={5} max={1440} value={interval} onChange={(e) => setInterval_(e.target.value)} /><span className="text-sm">min</span>
            <button className="btn-outline !py-1" onClick={saveInterval}>OK</button></div>
          <label className="mt-1 flex items-center gap-1 text-xs text-slate-500"><input type="checkbox" checked={applyAll} onChange={(e) => setApplyAll(e.target.checked)} /> Appliquer à toutes les sources</label></div>
      </div>

      <h2 className="mb-2 text-sm font-semibold">Sources</h2>
      <div className="card mb-6 overflow-x-auto"><table className="w-full">
        <thead><tr className="border-b border-slate-200 dark:border-slate-800"><th className="th">Source</th><th className="th">État</th><th className="th">Dernière collecte réussie</th><th className="th">Échecs</th></tr></thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {s.sources.map((x) => (
            <tr key={x.id}><td className="td font-medium">{x.name}</td><td className="td"><StatusBadge status={x.status} active={x.is_active} /></td>
              <td className="td text-xs">{x.last_success_at ? `${timeAgo(x.last_success_at)} (${formatDateTime(x.last_success_at)})` : "jamais"}</td>
              <td className="td text-xs">{x.consecutive_failures || "—"}{x.last_error && <p className="max-w-md text-red-600">{x.last_error}</p>}</td></tr>
          ))}
        </tbody></table></div>

      <h2 className="mb-2 text-sm font-semibold">Journal de collecte</h2>
      <div className="card overflow-x-auto"><table className="w-full">
        <thead><tr className="border-b border-slate-200 dark:border-slate-800"><th className="th">Début</th><th className="th">Source</th><th className="th">Résultat</th><th className="th">Trouvés</th><th className="th">Nouveaux</th><th className="th">Doublons</th><th className="th">Erreurs</th></tr></thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {(logs.data || []).length === 0 && <tr><td className="td text-slate-500" colSpan={7}>Aucune collecte pour l'instant.</td></tr>}
          {(logs.data || []).map((l) => (
            <tr key={l.id}><td className="td text-xs">{formatDateTime(l.started_at)}</td><td className="td">{l.source_name}</td>
              <td className="td"><StatusBadge status={l.status} />{l.message && <p className="mt-1 max-w-xs text-xs text-slate-500">{l.message}</p>}</td>
              <td className="td">{l.found}</td><td className="td">{l.new}</td><td className="td">{l.duplicates}</td><td className="td">{l.errors}</td></tr>
          ))}
        </tbody></table></div>
    </>
  );
}
