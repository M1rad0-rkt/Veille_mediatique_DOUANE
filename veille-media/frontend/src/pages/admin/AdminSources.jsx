import { useEffect, useState } from "react";
import { Pencil, Play, Plus, Search, Trash2 } from "lucide-react";
import { ErrorBox, Field, Loading, Modal, PageTitle, Spinner, StatusBadge } from "../../components/ui";
import useAsync from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { agent, sources as api } from "../../services/endpoints";
import { timeAgo } from "../../utils/format";

const EMPTY = { name: "", base_url: "https://", type: "rss", feed_url: "", interval_minutes: 30, is_active: true, selectors: "" };

function SourceForm({ initial, onClose, onSaved }) {
  const [f, setF] = useState(initial ? { ...EMPTY, ...initial, feed_url: initial.feed_url || "", selectors: initial.selectors ? JSON.stringify(initial.selectors, null, 2) : "" } : EMPTY);
  const [error, setError] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const save = async (e) => {
    e.preventDefault(); setError("");
    let selectors = null;
    if (f.selectors.trim()) { try { selectors = JSON.parse(f.selectors); } catch { return setError("Les sélecteurs doivent être un JSON valide"); } }
    const body = { name: f.name, base_url: f.base_url, type: f.type, feed_url: f.feed_url || null, interval_minutes: Number(f.interval_minutes), is_active: f.is_active, selectors };
    try { initial ? await api.update(initial.id, body) : await api.create(body); onSaved(); onClose(); }
    catch (err) { setError(errorMessage(err)); }
  };
  return (
    <Modal title={initial ? "Modifier la source" : "Nouvelle source"} onClose={onClose}>
      <form onSubmit={save} className="space-y-3">
        <Field label="Nom"><input className="input" required value={f.name} onChange={set("name")} /></Field>
        <Field label="Adresse du site"><input className="input" required value={f.base_url} onChange={set("base_url")} /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Type de collecte">
            <select className="input" value={f.type} onChange={set("type")}>
              <option value="rss">Flux RSS</option><option value="sitemap">Sitemap</option><option value="html">Page HTML (sélecteurs)</option>
            </select>
          </Field>
          <Field label="Fréquence (minutes)"><input className="input" type="number" min={5} max={1440} value={f.interval_minutes} onChange={set("interval_minutes")} /></Field>
        </div>
        <Field label="Adresse du flux / sitemap (vide = détection automatique)"><input className="input" value={f.feed_url} onChange={set("feed_url")} /></Field>
        {f.type === "html" && <Field label='Sélecteurs JSON, ex. {"link": "h2 a", "url_contains": "/actualites/"}'><textarea className="input font-mono text-xs" rows={3} value={f.selectors} onChange={set("selectors")} /></Field>}
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.is_active} onChange={set("is_active")} /> Source active</label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2"><button type="button" className="btn-ghost" onClick={onClose}>Annuler</button><button className="btn-primary">Enregistrer</button></div>
      </form>
    </Modal>
  );
}

function ProbeModal({ source, onClose, onApplied }) {
  const [res, setRes] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const run = async (apply) => {
    setBusy(true); setError("");
    try { const r = await api.probe(source.id, apply); setRes(r); if (r.applied) onApplied(); } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  };
  useEffect(() => { run(false); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <Modal title={`Diagnostic : ${source.name}`} onClose={onClose}>
      {busy && !res && <div className="flex items-center gap-2 text-sm"><Spinner /> Analyse du site en cours (robots.txt, flux, sitemap)…</div>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {res && (
        <div className="space-y-2 text-sm">
          <p>robots.txt : {res.robots_ok === null ? "non vérifié" : res.robots_ok ? "collecte autorisée" : <b className="text-red-600">collecte interdite</b>}</p>
          <p>Flux RSS : {res.feed_url ? `${res.feed_url} (${res.feed_items} articles)` : "aucun trouvé"}</p>
          <p>Sitemap : {res.sitemap_url || "aucun trouvé"}</p>
          {res.notes.map((n, i) => <p key={i} className="text-slate-500">• {n}</p>)}
          {res.applied && <p className="font-medium text-emerald-600">Source configurée et activée ({res.recommended_type}).</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button className="btn-ghost" onClick={onClose}>Fermer</button>
            {res.robots_ok && res.recommended_type && !res.applied && <button className="btn-primary" disabled={busy} onClick={() => run(true)}>Appliquer et activer</button>}
          </div>
        </div>
      )}
    </Modal>
  );
}

export default function AdminSources() {
  const { data, loading, error, reload } = useAsync(() => api.list(), []);
  const [form, setForm] = useState(null);      // null | "new" | source
  const [probe, setProbe] = useState(null);
  const [msg, setMsg] = useState("");

  const act = async (fn, ok) => { try { await fn(); setMsg(ok || ""); reload(); } catch (e) { setMsg(errorMessage(e)); } };
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  return (
    <>
      <PageTitle title="Sources d'actualités" subtitle="Ajoutez, modifiez, activez ou désactivez les médias surveillés"
        actions={<button className="btn-primary" onClick={() => setForm("new")}><Plus className="h-4 w-4" /> Ajouter une source</button>} />
      {msg && <p role="status" className="mb-3 text-sm text-slate-600 dark:text-slate-300">{msg}</p>}
      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead><tr className="border-b border-slate-200 dark:border-slate-800"><th className="th">Source</th><th className="th">Type</th><th className="th">État</th><th className="th">Dernière collecte</th><th className="th">Fréq.</th><th className="th" /></tr></thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {data.map((s) => (
              <tr key={s.id}>
                <td className="td"><p className="font-medium">{s.name}</p><p className="text-xs text-slate-500">{s.base_url}</p>{s.last_error && <p className="mt-1 max-w-xs text-xs text-red-600">{s.last_error}</p>}</td>
                <td className="td uppercase text-xs">{s.type}{s.robots_ok === false && <span className="ml-1 text-red-600">robots✗</span>}</td>
                <td className="td"><StatusBadge status={s.status} active={s.is_active} /></td>
                <td className="td text-xs">{timeAgo(s.last_success_at)}</td>
                <td className="td text-xs">{s.interval_minutes} min</td>
                <td className="td"><div className="flex justify-end gap-1">
                  <button className="btn-ghost !p-1.5" title="Diagnostiquer" onClick={() => setProbe(s)}><Search className="h-4 w-4" /></button>
                  <button className="btn-ghost !p-1.5" title="Collecter maintenant" disabled={!s.is_active} onClick={() => act(() => agent.collect(s.id), "Collecte demandée : le worker la lance dans quelques secondes")}><Play className="h-4 w-4" /></button>
                  <button className="btn-ghost !p-1.5" title={s.is_active ? "Désactiver" : "Activer"} onClick={() => act(() => api.update(s.id, { is_active: !s.is_active }))}>{s.is_active ? "Off" : "On"}</button>
                  <button className="btn-ghost !p-1.5" title="Modifier" onClick={() => setForm(s)}><Pencil className="h-4 w-4" /></button>
                  <button className="btn-ghost !p-1.5 text-red-600" title="Supprimer" onClick={() => window.confirm(`Supprimer « ${s.name} » ?`) && act(() => api.remove(s.id), "Source supprimée")}><Trash2 className="h-4 w-4" /></button>
                </div></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {form && <SourceForm initial={form === "new" ? null : form} onClose={() => setForm(null)} onSaved={reload} />}
      {probe && <ProbeModal source={probe} onClose={() => setProbe(null)} onApplied={reload} />}
    </>
  );
}
