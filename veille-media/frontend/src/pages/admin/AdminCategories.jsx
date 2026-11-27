import { useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { ErrorBox, Field, Loading, Modal, PageTitle } from "../../components/ui";
import useAsync from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { categories as api } from "../../services/endpoints";
import { NAV_LABELS } from "../../utils/format";

function CategoryForm({ initial, onClose, onSaved }) {
  const [f, setF] = useState(initial || { slug: "", name: "", color: "#64748b", nav_group: "autres", position: 99, is_active: true });
  const [error, setError] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const save = async (e) => {
    e.preventDefault();
    try {
      const body = { name: f.name, color: f.color, nav_group: f.nav_group, position: Number(f.position), is_active: f.is_active };
      initial ? await api.update(initial.id, body) : await api.create({ ...body, slug: f.slug });
      onSaved(); onClose();
    } catch (err) { setError(errorMessage(err)); }
  };
  return (
    <Modal title={initial ? "Modifier la catégorie" : "Nouvelle catégorie"} onClose={onClose}>
      <form onSubmit={save} className="space-y-3">
        <Field label="Nom"><input className="input" required value={f.name} onChange={set("name")} /></Field>
        {!initial && <Field label="Identifiant (minuscules, tirets)"><input className="input" required pattern="[a-z0-9]+(-[a-z0-9]+)*" value={f.slug} onChange={set("slug")} /></Field>}
        <div className="grid grid-cols-3 gap-3">
          <Field label="Couleur"><input type="color" className="input !p-1" value={f.color} onChange={set("color")} /></Field>
          <Field label="Navigation"><select className="input" value={f.nav_group} onChange={set("nav_group")}>{Object.entries(NAV_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
          <Field label="Position"><input type="number" className="input" value={f.position} onChange={set("position")} /></Field>
        </div>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.is_active} onChange={set("is_active")} /> Active (proposée à l'IA et dans les filtres)</label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2"><button type="button" className="btn-ghost" onClick={onClose}>Annuler</button><button className="btn-primary">Enregistrer</button></div>
      </form>
    </Modal>
  );
}

export default function AdminCategories() {
  const { data, loading, error, reload } = useAsync(() => api.list(true), []);
  const [form, setForm] = useState(null);
  const [msg, setMsg] = useState("");
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  const remove = async (c) => { if (!window.confirm(`Supprimer « ${c.name} » ?`)) return; try { await api.remove(c.id); setMsg(""); reload(); } catch (e) { setMsg(errorMessage(e)); } };
  return (
    <>
      <PageTitle title="Catégories" subtitle="Les catégories actives sont proposées à l'IA pour classer les articles"
        actions={<button className="btn-primary" onClick={() => setForm("new")}><Plus className="h-4 w-4" /> Ajouter</button>} />
      {msg && <p role="alert" className="mb-3 text-sm text-red-600">{msg}</p>}
      <div className="card overflow-x-auto"><table className="w-full">
        <thead><tr className="border-b border-slate-200 dark:border-slate-800"><th className="th">Catégorie</th><th className="th">Navigation</th><th className="th">Articles</th><th className="th">État</th><th className="th" /></tr></thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {data.map((c) => (
            <tr key={c.id}>
              <td className="td"><span className="mr-2 inline-block h-3 w-3 rounded-full align-middle" style={{ backgroundColor: c.color }} />{c.name} <span className="text-xs text-slate-400">({c.slug})</span></td>
              <td className="td text-xs">{NAV_LABELS[c.nav_group] || c.nav_group}</td>
              <td className="td">{c.article_count}</td>
              <td className="td text-xs">{c.is_active ? "Active" : "Désactivée"}</td>
              <td className="td"><div className="flex justify-end gap-1">
                <button className="btn-ghost !p-1.5" onClick={() => setForm(c)} title="Modifier"><Pencil className="h-4 w-4" /></button>
                <button className="btn-ghost !p-1.5 text-red-600" onClick={() => remove(c)} title="Supprimer"><Trash2 className="h-4 w-4" /></button>
              </div></td>
            </tr>
          ))}
        </tbody></table></div>
      {form && <CategoryForm initial={form === "new" ? null : form} onClose={() => setForm(null)} onSaved={reload} />}
    </>
  );
}
