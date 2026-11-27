export default function Pagination({ page, pages, total, onPage }) {
  if (pages <= 1) return total ? <p className="mt-4 text-center text-xs text-slate-500">{total} actualité(s)</p> : null;
  return (
    <div className="mt-6 flex items-center justify-between text-sm">
      <span className="text-slate-500">{total} actualités · page {page} / {pages}</span>
      <div className="flex gap-2">
        <button className="btn-outline" disabled={page <= 1} onClick={() => onPage(page - 1)}>Précédent</button>
        <button className="btn-outline" disabled={page >= pages} onClick={() => onPage(page + 1)}>Suivant</button>
      </div>
    </div>
  );
}
