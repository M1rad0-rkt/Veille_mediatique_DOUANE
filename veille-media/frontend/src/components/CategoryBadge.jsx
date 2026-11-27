export default function CategoryBadge({ category }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 px-2 py-0.5 text-xs dark:border-slate-700"
          title={category.origin === "manual" ? "Catégorie corrigée manuellement" : "Catégorie attribuée par l'IA"}>
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: category.color }} />
      {category.name}
    </span>
  );
}
