import { useEffect, useState } from "react";
import { ArrowLeft, ExternalLink, RefreshCw, Star } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import CategoryBadge from "../components/CategoryBadge";
import SummaryBlock from "../components/SummaryBlock";
import { ErrorBox, Loading, Modal, Spinner } from "../components/ui";
import { useAuth } from "../contexts/AuthContext";
import useAsync from "../hooks/useAsync";
import { errorMessage } from "../services/api";
import { categories as categoriesApi, news as newsApi } from "../services/endpoints";
import { publishedLabel } from "../utils/format";

function CategoryEditor({ item, onClose, onSaved }) {
  const { data: cats } = useAsync(() => categoriesApi.list(), []);
  const [selected, setSelected] = useState(item.categories.map((c) => c.id));
  const [primary, setPrimary] = useState(item.categories.find((c) => c.is_primary)?.id ?? item.categories[0]?.id);
  const [error, setError] = useState("");
  const toggle = (id) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : s.length < 5 ? [...s, id] : s));
  const save = async () => {
    try { onSaved(await newsApi.setCategory(item.id, { category_ids: selected, primary_category_id: primary })); onClose(); }
    catch (e) { setError(errorMessage(e)); }
  };
  return (
    <Modal title="Corriger la catégorie" onClose={onClose}>
      <p className="mb-3 text-sm text-slate-500">Cochez les thématiques (5 max) et choisissez la principale. Une correction manuelle n'est jamais écrasée par l'IA.</p>
      <div className="max-h-72 space-y-1 overflow-y-auto">
        {(cats || []).map((c) => (
          <div key={c.id} className="flex items-center justify-between rounded-lg px-2 py-1.5 hover:bg-slate-50 dark:hover:bg-slate-800">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={selected.includes(c.id)} onChange={() => { toggle(c.id); if (primary === c.id) setPrimary(undefined); }} />
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: c.color }} />{c.name}
            </label>
            {selected.includes(c.id) && (
              <label className="flex items-center gap-1 text-xs text-slate-500">
                <input type="radio" name="primary" checked={primary === c.id} onChange={() => setPrimary(c.id)} /> principale
              </label>
            )}
          </div>
        ))}
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      <div className="mt-4 flex justify-end gap-2">
        <button className="btn-ghost" onClick={onClose}>Annuler</button>
        <button className="btn-primary" disabled={!selected.length || !primary} onClick={save}>Enregistrer</button>
      </div>
    </Modal>
  );
}

export default function NewsDetail() {
  const { id } = useParams();
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const { data: item, loading, error, reload, setData } = useAsync(() => newsApi.detail(id), [id]);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  // Ouvrir le détail = marquer comme lu.
  useEffect(() => {
    if (item && !item.is_read) newsApi.read(item.id, true).then(() => setData({ ...item, is_read: true })).catch(() => {});
  }, [item?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading && !item) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  const toggleFav = async () => { const on = !item.is_favorite; setData({ ...item, is_favorite: on }); try { await newsApi.favorite(item.id, on); } catch { setData(item); } };
  const markUnread = async () => { await newsApi.read(item.id, false); setData({ ...item, is_read: false }); setNotice("Marqué comme non lu"); };
  const reprocess = async () => {
    setBusy(true); setNotice("");
    try { setData(await newsApi.reprocess(item.id)); setNotice("Classification et résumé régénérés"); }
    catch (e) { setNotice(errorMessage(e)); } finally { setBusy(false); }
  };
  const s = item.summary;

  return (
    <div className="mx-auto max-w-3xl">
      <button className="btn-ghost mb-3 !px-2" onClick={() => navigate(-1)}><ArrowLeft className="h-4 w-4" /> Retour</button>
      <article className="card space-y-5 p-5 sm:p-7">
        {item.image_url && <img src={item.image_url} alt="" referrerPolicy="no-referrer" className="max-h-80 w-full rounded-lg object-cover" onError={(e) => (e.currentTarget.style.display = "none")} />}
        <header className="space-y-2">
          <div className="flex flex-wrap gap-1.5">{item.categories.map((c) => <CategoryBadge key={c.id} category={c} />)}</div>
          <h1 className="text-2xl font-semibold leading-snug">{item.title}</h1>
          <p className="text-sm text-slate-500">
            <span className="font-medium text-slate-700 dark:text-slate-300">{item.source.name}</span> · <span className={item.published_at ? "" : "italic"}>{publishedLabel(item)}</span>
            {item.author && <> · {item.author}</>}
          </p>
        </header>

        <SummaryBlock news={item} />

        {s?.status === "ok" && s.key_points?.length > 0 && (
          <section><h2 className="mb-1 text-sm font-semibold">Informations essentielles</h2>
            <ul className="list-disc space-y-1 pl-5 text-sm">{s.key_points.map((k, i) => <li key={i}>{k}</li>)}</ul>
          </section>
        )}
        {s?.status === "ok" && s.entities && Object.values(s.entities).some((v) => v?.length) && (
          <section><h2 className="mb-1 text-sm font-semibold">Personnes et organisations concernées</h2>
            <div className="space-y-1 text-sm">
              {[["people", "Personnes"], ["organizations", "Organisations"], ["places", "Lieux"]].map(([k, label]) =>
                s.entities[k]?.length ? <p key={k}><span className="text-slate-500">{label} : </span>{s.entities[k].join(", ")}</p> : null)}
            </div>
          </section>
        )}
        {item.content_is_partial && <p className="text-xs text-slate-500">Le texte intégral n'a pas pu être récupéré : consultez l'article original pour le détail complet.</p>}

        <div className="flex flex-wrap items-center gap-2 border-t border-slate-200 pt-4 dark:border-slate-800">
          <a className="btn-primary" href={item.url} target="_blank" rel="noopener noreferrer">Lire l'article original <ExternalLink className="h-4 w-4" /></a>
          <button className="btn-outline" onClick={toggleFav}><Star className={`h-4 w-4 ${item.is_favorite ? "fill-amber-400 text-amber-400" : ""}`} />{item.is_favorite ? "Dans les favoris" : "Ajouter aux favoris"}</button>
          <button className="btn-ghost" onClick={markUnread}>Marquer comme non lu</button>
          {isAdmin && <>
            <button className="btn-outline" onClick={() => setEditing(true)}>Corriger la catégorie</button>
            <button className="btn-outline" onClick={reprocess} disabled={busy}>{busy ? <Spinner /> : <RefreshCw className="h-4 w-4" />} Régénérer le résumé</button>
          </>}
        </div>
        {notice && <p role="status" className="text-sm text-slate-600 dark:text-slate-300">{notice}</p>}
      </article>

      {item.related.length > 0 && (
        <section className="mt-6">
          <h2 className="mb-2 text-sm font-semibold">Autres articles sur le même sujet</h2>
          <ul className="card divide-y divide-slate-100 dark:divide-slate-800">
            {item.related.map((r) => (
              <li key={r.id} className="p-3">
                <Link to={`/actualites/${r.id}`} className="text-sm font-medium hover:text-brand-600">{r.title}</Link>
                <p className="text-xs text-slate-500">{r.source.name} · {publishedLabel(r)}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
      {editing && <CategoryEditor item={item} onClose={() => setEditing(false)} onSaved={setData} />}
    </div>
  );
}
