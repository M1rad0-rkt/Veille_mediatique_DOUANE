const tz = "Indian/Antananarivo";

// Date de publication : si elle est inconnue, on l'affirme (jamais la date de collecte à la place).
export function publishedLabel(n) {
  if (!n.published_at) return "Date non disponible";
  return formatDateTime(n.published_at);
}

export function formatDateTime(iso) {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short", timeZone: tz }).format(new Date(iso));
}

export function timeAgo(iso) {
  if (!iso) return "jamais";
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "à l'instant";
  if (s < 3600) return `il y a ${Math.floor(s / 60)} min`;
  if (s < 86400) return `il y a ${Math.floor(s / 3600)} h`;
  return `il y a ${Math.floor(s / 86400)} j`;
}

export const NAV_LABELS = {
  economie: "Économie", politique: "Politique", societe: "Société", sante: "Santé", education: "Éducation",
  technologie: "Technologie", environnement: "Environnement", sport: "Sport", culture: "Culture", autres: "Autres",
};
