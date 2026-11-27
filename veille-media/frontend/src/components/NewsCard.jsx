import { useState } from "react";
import { ExternalLink, Star } from "lucide-react";
import { Link } from "react-router-dom";
import { news as newsApi } from "../services/endpoints";
import { publishedLabel } from "../utils/format";
import CategoryBadge from "./CategoryBadge";
import SummaryBlock from "./SummaryBlock";

export default function NewsCard({ item, onChange }) {
  const [fav, setFav] = useState(item.is_favorite);
  const [imgOk, setImgOk] = useState(true);

  const toggleFav = async () => {
    const next = !fav;
    setFav(next);                                   // mise à jour immédiate, annulée si l'API échoue
    try { await newsApi.favorite(item.id, next); onChange?.({ ...item, is_favorite: next }); }
    catch { setFav(!next); }
  };
  const openOriginal = () => { if (!item.is_read) newsApi.read(item.id, true).then(() => onChange?.({ ...item, is_read: true })).catch(() => {}); };

  return (
    <article className="card flex flex-col overflow-hidden sm:flex-row">
      {item.image_url && imgOk && (
        <img src={item.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" onError={() => setImgOk(false)}
             className="h-40 w-full shrink-0 object-cover sm:h-auto sm:w-48" />
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-2 p-4">
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          {!item.is_read && <span className="h-2 w-2 rounded-full bg-brand-500" title="Non lu" />}
          <span className="font-medium text-slate-700 dark:text-slate-300">{item.source.name}</span>
          <span>·</span>
          <span className={item.published_at ? "" : "italic"}>{publishedLabel(item)}</span>
        </div>
        <Link to={`/actualites/${item.id}`} className={`text-base leading-snug hover:text-brand-600 ${item.is_read ? "font-normal" : "font-semibold"}`}>
          {item.title}
        </Link>
        <SummaryBlock news={item} compact />
        <div className="mt-auto flex flex-wrap items-center justify-between gap-2 pt-1">
          <div className="flex flex-wrap gap-1.5">{item.categories.map((c) => <CategoryBadge key={c.id} category={c} />)}</div>
          <div className="flex items-center gap-1">
            <button className="btn-ghost !px-2" onClick={toggleFav} aria-pressed={fav} title={fav ? "Retirer des favoris" : "Ajouter aux favoris"}>
              <Star className={`h-4 w-4 ${fav ? "fill-amber-400 text-amber-400" : ""}`} />
            </button>
            <a className="btn-outline" href={item.url} target="_blank" rel="noopener noreferrer" onClick={openOriginal}>
              Lire l'original <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
        </div>
      </div>
    </article>
  );
}
