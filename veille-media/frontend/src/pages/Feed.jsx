import { useCallback, useMemo } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import Filters from "../components/Filters";
import NewsCard from "../components/NewsCard";
import Pagination from "../components/Pagination";
import { EmptyState, ErrorBox, Loading, PageTitle } from "../components/ui";
import { useNewsPoll } from "../contexts/NewsPollContext";
import useAsync from "../hooks/useAsync";
import { categories as categoriesApi, news as newsApi, sources as sourcesApi } from "../services/endpoints";
import { NAV_LABELS } from "../utils/format";

const TITLES = { all: "Fil d'actualités", favorites: "Mes favoris", history: "Historique de lecture" };

export default function Feed({ mode = "all" }) {
  const { group } = useParams();
  const [params, setSearch] = useSearchParams();
  const { newCount, refreshKey, acknowledge } = useNewsPoll();

  // Fusionne des changements de filtres dans l'URL ; tout changement de filtre revient à la page 1.
  const setParams = useCallback((changes) => {
    setSearch((prev) => {
      const next = new URLSearchParams(prev);
      Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
      if (!("page" in changes)) next.delete("page");
      return next;
    }, { replace: true });
  }, [setSearch]);

  const { data: cats } = useAsync(() => categoriesApi.list(), []);
  const { data: srcs } = useAsync(() => sourcesApi.list(), []);

  const query = useMemo(() => ({
    q: params.get("q"), category: params.get("category"), source_id: params.get("source_id"),
    date_from: params.get("date_from"), date_to: params.get("date_to"), read_status: params.get("read_status"),
    page: params.get("page") || 1, page_size: 20, nav_group: mode === "all" ? group : undefined,
  }), [params, mode, group]);

  const fetcher = mode === "favorites" ? newsApi.favorites : mode === "history" ? newsApi.history : newsApi.list;
  const { data, loading, error, reload, setData } = useAsync(() => fetcher(query), [query, mode, refreshKey]);

  const title = group ? NAV_LABELS[group] || group : TITLES[mode];
  const page = Number(params.get("page") || 1);
  const updateItem = (updated) => setData({ ...data, items: data.items.map((i) => (i.id === updated.id ? updated : i)) });

  return (
    <>
      <PageTitle title={title} subtitle="Les plus récentes d'abord" />
      <Filters params={params} setParams={setParams} categories={cats || []} sources={srcs || []} hideCategory={!!group} />
      {newCount > 0 && page === 1 && (
        <button className="btn-primary mb-4 w-full justify-center" onClick={acknowledge}>
          {newCount} nouvelle(s) actualité(s) collectée(s) — afficher
        </button>
      )}
      {error ? <ErrorBox message={error} onRetry={reload} /> : loading && !data ? <Loading /> : (
        <>
          {data.items.length === 0 ? (
            <EmptyState title="Aucune actualité à afficher"
                        hint={mode === "all" ? "Modifiez les filtres, ou attendez la prochaine collecte." : "Rien ici pour l'instant."} />
          ) : (
            <div className={`space-y-3 transition-opacity ${loading ? "opacity-60" : ""}`}>
              {data.items.map((item) => <NewsCard key={item.id} item={item} onChange={updateItem} />)}
            </div>
          )}
          <Pagination page={data.page} pages={data.pages} total={data.total} onPage={(p) => { setParams({ page: String(p) }); window.scrollTo({ top: 0 }); }} />
        </>
      )}
    </>
  );
}
