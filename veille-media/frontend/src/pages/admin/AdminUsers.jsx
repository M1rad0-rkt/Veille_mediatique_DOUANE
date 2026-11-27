import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { ErrorBox, Field, Loading, Modal, PageTitle } from "../../components/ui";
import { useAuth } from "../../contexts/AuthContext";
import useAsync from "../../hooks/useAsync";
import { errorMessage } from "../../services/api";
import { admin as api } from "../../services/endpoints";
import { formatDateTime } from "../../utils/format";

function UserForm({ onClose, onSaved }) {
  const [f, setF] = useState({ full_name: "", email: "", password: "", role: "user" });
  const [error, setError] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const save = async (e) => {
    e.preventDefault();
    try { await api.createUser(f); onSaved(); onClose(); } catch (err) { setError(errorMessage(err)); }
  };
  return (
    <Modal title="Nouvel utilisateur" onClose={onClose}>
      <form onSubmit={save} className="space-y-3">
        <Field label="Nom complet"><input className="input" required minLength={2} value={f.full_name} onChange={set("full_name")} /></Field>
        <Field label="E-mail"><input className="input" type="email" required value={f.email} onChange={set("email")} /></Field>
        <Field label="Mot de passe provisoire (10 caractères minimum)"><input className="input" type="password" required minLength={10} autoComplete="new-password" value={f.password} onChange={set("password")} /></Field>
        <Field label="Rôle"><select className="input" value={f.role} onChange={set("role")}><option value="user">Agent de communication</option><option value="admin">Administrateur</option></select></Field>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2"><button type="button" className="btn-ghost" onClick={onClose}>Annuler</button><button className="btn-primary">Créer</button></div>
      </form>
    </Modal>
  );
}

export default function AdminUsers() {
  const { user: me } = useAuth();
  const { data, loading, error, reload } = useAsync(() => api.users(), []);
  const [creating, setCreating] = useState(false);
  const [msg, setMsg] = useState("");
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  const act = async (fn) => { try { await fn(); setMsg(""); reload(); } catch (e) { setMsg(errorMessage(e)); } };
  return (
    <>
      <PageTitle title="Utilisateurs" subtitle="Pas d'inscription publique : les comptes sont créés ici"
        actions={<button className="btn-primary" onClick={() => setCreating(true)}><Plus className="h-4 w-4" /> Nouvel utilisateur</button>} />
      {msg && <p role="alert" className="mb-3 text-sm text-red-600">{msg}</p>}
      <div className="card overflow-x-auto"><table className="w-full">
        <thead><tr className="border-b border-slate-200 dark:border-slate-800"><th className="th">Utilisateur</th><th className="th">Rôle</th><th className="th">Dernière connexion</th><th className="th">Compte</th><th className="th" /></tr></thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {data.map((u) => (
            <tr key={u.id}>
              <td className="td"><p className="font-medium">{u.full_name}</p><p className="text-xs text-slate-500">{u.email}</p></td>
              <td className="td">
                <select className="input !w-auto !py-1" value={u.role} disabled={u.id === me.id} onChange={(e) => act(() => api.updateUser(u.id, { role: e.target.value }))}>
                  <option value="user">Agent</option><option value="admin">Administrateur</option>
                </select>
              </td>
              <td className="td text-xs">{formatDateTime(u.last_login_at)}</td>
              <td className="td"><button className="btn-outline !py-1" disabled={u.id === me.id} onClick={() => act(() => api.updateUser(u.id, { is_active: !u.is_active }))}>{u.is_active ? "Actif — désactiver" : "Désactivé — activer"}</button></td>
              <td className="td text-right"><button className="btn-ghost !p-1.5 text-red-600" disabled={u.id === me.id} title="Supprimer"
                onClick={() => window.confirm(`Supprimer le compte de ${u.full_name} ?`) && act(() => api.deleteUser(u.id))}><Trash2 className="h-4 w-4" /></button></td>
            </tr>
          ))}
        </tbody></table></div>
      {creating && <UserForm onClose={() => setCreating(false)} onSaved={reload} />}
    </>
  );
}
