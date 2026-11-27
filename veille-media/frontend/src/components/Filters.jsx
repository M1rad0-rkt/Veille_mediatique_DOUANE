import { Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import useDebounce from "../hooks/useDebounce";

// Filtres combinables ; l'état vit dans l'URL (partageable, bouton « retour » fonctionnel).
export default function Filters({ params, setParams, categories, sources, hideCategory = false }) {
  const [q, setQ] = useState(params.get("q") || "");
  const debounced = useDebounce(q, 400);
  useEffect(() => { setQ(params.get("q") || ""); }, [params.get("q")]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (debounced !== (params.get("q") || "")) setParams({ q: debounced }); }, [debounced]); // eslint-disable-line react-hooks/exhaustive-deps

  const val = (k, d = "") => params.get(k) || d;
  const hasFilters = ["q", "category", "source_id", "date_from", "date_to", "read_status"].some((k) => params.get(k));

  return (
    <div className="card mb-5 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-6">
      <label className="relative sm:col-span-2">
        <span className="label">Mot-clé</span>
        <Search className="absolute left-3 top-[34px] h-4 w-4 text-slate-400" />
        <input className="input pl-9" placeholder="Rechercher…" value={q} onChange={(e) => setQ(e.target.value)} />
      </label>
      {!hideCategory && (
        <label><span className="label">Catégorie</span>
          <select className="input" value={val("category")} onChange={(e) => setParams({ category: e.target.value })}>
            <option value="">Toutes</option>
            {categories.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
          </select>
        </label>
      )}
      <label><span className="label">Source</span>
        <select className="input" value={val("source_id")} onChange={(e) => setParams({ source_id: e.target.value })}>
          <option value="">Toutes</option>
          {sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </label>
      <label><span className="label">Statut</span>
        <select className="input" value={val("read_status", "all")} onChange={(e) => setParams({ read_status: e.target.value === "all" ? "" : e.target.value })}>
          <option value="all">Tous</option><option value="unread">Non lus</option><option value="read">Lus</option>
        </select>
      </label>
      <label><span className="label">Du</span>
        <input type="date" className="input" value={val("date_from")} onChange={(e) => setParams({ date_from: e.target.value })} />
      </label>
      <label><span className="label">Au</span>
        <input type="date" className="input" value={val("date_to")} onChange={(e) => setParams({ date_to: e.target.value })} />
      </label>
      {hasFilters && (
        <div className="flex items-end">
          <button className="btn-ghost" onClick={() => { setQ(""); setParams({ q: "", category: "", source_id: "", date_from: "", date_to: "", read_status: "" }); }}>
            <X className="h-4 w-4" /> Réinitialiser
          </button>
        </div>
      )}
    </div>
  );
}
