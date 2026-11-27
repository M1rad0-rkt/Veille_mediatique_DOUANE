import { Sparkles } from "lucide-react";

// Affiche le résumé IA, ou un message honnête s'il n'existe pas. Rien n'est inventé côté interface.
export default function SummaryBlock({ news, compact = false }) {
  const s = news.summary;
  if (s?.status === "ok" && s.summary) {
    return (
      <div>
        <p className="mb-1 flex items-center gap-1 text-[11px] font-medium uppercase tracking-wide text-brand-600">
          <Sparkles className="h-3 w-3" /> Résumé généré par IA
        </p>
        <p className={`text-sm leading-relaxed ${compact ? "line-clamp-4" : ""}`}>{s.summary}</p>
      </div>
    );
  }
  const msg = !s
    ? "Résumé en cours de génération…"
    : s.status === "insufficient_content"
      ? "Résumé non disponible : contenu insuffisant pour en produire un fiable."
      : "Résumé non disponible : la génération a échoué.";
  return (
    <div>
      <p className="text-sm italic text-slate-500">{msg}</p>
      {news.excerpt && <p className={`mt-1 text-sm text-slate-600 dark:text-slate-400 ${compact ? "line-clamp-3" : ""}`}>{news.excerpt}</p>}
    </div>
  );
}
