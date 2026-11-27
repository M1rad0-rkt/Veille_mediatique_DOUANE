import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ErrorBox, Loading, PageTitle } from "../components/ui";
import { useAuth } from "../contexts/AuthContext";
import { useNewsPoll } from "../contexts/NewsPollContext";
import useAsync from "../hooks/useAsync";
import { dashboard } from "../services/endpoints";
import { formatDateTime, timeAgo } from "../utils/format";

const Stat = ({ label, value, hint }) => (
  <div className="card p-4">
    <p className="text-xs text-slate-500">{label}</p>
    <p className="mt-1 text-2xl font-semibold">{value}</p>
    {hint && <p className="mt-0.5 text-xs text-slate-400">{hint}</p>}
  </div>
);

export default function Dashboard() {
  const { isAdmin } = useAuth();
  const { refreshKey } = useNewsPoll();
  const { data: d, loading, error, reload } = useAsync(() => (isAdmin ? dashboard.admin() : dashboard.me()), [isAdmin, refreshKey]);
  if (loading && !d) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  const series = d.daily_series.map((p) => ({ ...p, label: p.day.slice(8, 10) + "/" + p.day.slice(5, 7) }));
  const cats = d.by_category.filter((c) => c.count > 0);
  return (
    <>
      <PageTitle title="Tableau de bord" subtitle={`Dernière synchronisation : ${d.last_sync ? `${timeAgo(d.last_sync)} (${formatDateTime(d.last_sync)})` : "aucune pour l'instant"}`} />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Actualités collectées" value={d.total_news} />
        <Stat label="Actualités du jour" value={d.today_news} />
        <Stat label="Non lues" value={d.unread_news} />
        <Stat label="Sources actives" value={d.active_sources} />
        {isAdmin && <>
          <Stat label="Utilisateurs" value={d.users_count} />
          <Stat label="Sources en erreur" value={d.sources_in_error} />
          <Stat label="En attente de traitement IA" value={d.pending_ai} />
          <Stat label="Résumés en échec" value={d.summaries_failed} />
        </>}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <section className="card p-4 lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold">Évolution des actualités (30 jours)</h2>
          <div className="h-64">
            <ResponsiveContainer>
              <LineChart data={series} margin={{ left: -20, right: 8, top: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} interval={4} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="count" name="Articles" stroke="#3b6cf6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="card p-4">
          <h2 className="mb-3 text-sm font-semibold">Répartition par catégorie</h2>
          {cats.length === 0 ? <p className="py-16 text-center text-sm text-slate-500">Aucune actualité classée pour l'instant.</p> : (
            <div className="h-64">
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={cats} dataKey="count" nameKey="name" innerRadius={45} outerRadius={80} paddingAngle={2}>
                    {cats.map((c) => <Cell key={c.slug} fill={c.color} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>
      </div>

      <section className="card mt-4 p-4">
        <h2 className="mb-3 text-sm font-semibold">Articles par catégorie</h2>
        <div className="h-72">
          <ResponsiveContainer>
            <BarChart data={d.by_category} layout="vertical" margin={{ left: 40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" horizontal={false} />
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" name="Articles" radius={[0, 4, 4, 0]}>
                {d.by_category.map((c) => <Cell key={c.slug} fill={c.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </>
  );
}
