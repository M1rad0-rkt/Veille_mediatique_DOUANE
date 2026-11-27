import { useEffect, useState } from "react";
import { Activity, Bell, History, LayoutDashboard, LogOut, Menu, Moon, Newspaper, Radio, Search, Star, Sun, Tags, Users, X } from "lucide-react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { NewsPollProvider, useNewsPoll } from "../contexts/NewsPollContext";
import { useTheme } from "../contexts/ThemeContext";
import useAsync from "../hooks/useAsync";
import { categories } from "../services/endpoints";
import { NAV_LABELS } from "../utils/format";

const linkCls = ({ isActive }) =>
  `flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-sm transition ${
    isActive ? "bg-brand-50 font-medium text-brand-700 dark:bg-brand-600/20 dark:text-brand-100"
             : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"}`;

function Sidebar({ onNavigate }) {
  const { isAdmin } = useAuth();
  const { refreshKey } = useNewsPoll();
  const { data: groups } = useAsync(() => categories.nav(), [refreshKey]);
  const Item = ({ to, icon: Icon, children, count }) => (
    <NavLink to={to} end className={linkCls} onClick={onNavigate}>
      <span className="flex items-center gap-2">{Icon && <Icon className="h-4 w-4" />}{children}</span>
      {count != null && <span className="text-xs text-slate-400">{count}</span>}
    </NavLink>
  );
  return (
    <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
      <Item to="/" icon={LayoutDashboard}>Tableau de bord</Item>
      <Item to="/actualites" icon={Newspaper}>Fil d'actualités</Item>
      <p className="mt-4 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Catégories</p>
      {(groups || []).map((g) => (
        <Item key={g.nav_group} to={`/categorie/${g.nav_group}`} count={g.count}>{NAV_LABELS[g.nav_group] || g.nav_group}</Item>
      ))}
      <p className="mt-4 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Mon espace</p>
      <Item to="/favoris" icon={Star}>Favoris</Item>
      <Item to="/historique" icon={History}>Historique de lecture</Item>
      {isAdmin && (
        <>
          <p className="mt-4 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Administration</p>
          <Item to="/admin/agent" icon={Activity}>Agent de collecte</Item>
          <Item to="/admin/sources" icon={Radio}>Sources</Item>
          <Item to="/admin/categories" icon={Tags}>Catégories</Item>
          <Item to="/admin/utilisateurs" icon={Users}>Utilisateurs</Item>
        </>
      )}
    </nav>
  );
}

function Topbar({ onMenu }) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const { newCount, acknowledge } = useNewsPoll();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  return (
    <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90">
      <button className="btn-ghost !p-2 lg:hidden" onClick={onMenu} aria-label="Menu"><Menu className="h-5 w-5" /></button>
      <form className="relative max-w-xl flex-1" onSubmit={(e) => { e.preventDefault(); navigate(`/actualites?q=${encodeURIComponent(q.trim())}`); }}>
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <input className="input pl-9" placeholder="Rechercher dans les actualités…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Recherche" />
      </form>
      <div className="ml-auto flex items-center gap-1">
        <button className="btn-ghost relative !p-2" title={newCount ? `${newCount} nouvelle(s) actualité(s)` : "Aucune nouvelle actualité"}
                onClick={() => { acknowledge(); navigate("/actualites"); }} aria-label="Notifications">
          <Bell className="h-5 w-5" />
          {newCount > 0 && <span className="absolute -right-0.5 -top-0.5 min-w-[18px] rounded-full bg-red-500 px-1 text-center text-[10px] font-bold text-white">{newCount > 99 ? "99+" : newCount}</span>}
        </button>
        <button className="btn-ghost !p-2" onClick={toggle} aria-label="Changer de thème">{theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}</button>
        <div className="mx-2 hidden text-right text-xs leading-tight sm:block">
          <p className="font-medium">{user.full_name}</p>
          <p className="text-slate-500">{user.role === "admin" ? "Administrateur" : "Agent de communication"}</p>
        </div>
        <button className="btn-ghost !p-2" onClick={logout} title="Se déconnecter" aria-label="Se déconnecter"><LogOut className="h-5 w-5" /></button>
      </div>
    </header>
  );
}

function Shell() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  useEffect(() => setOpen(false), [location.pathname]);
  return (
    <div className="min-h-screen lg:pl-64">
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200 bg-white transition-transform dark:border-slate-800 dark:bg-slate-900 lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex items-center justify-between px-5 py-4">
          <span className="flex items-center gap-2 text-lg font-semibold"><Newspaper className="h-5 w-5 text-brand-600" /> Veille Média</span>
          <button className="btn-ghost !p-1 lg:hidden" onClick={() => setOpen(false)} aria-label="Fermer"><X className="h-5 w-5" /></button>
        </div>
        <Sidebar onNavigate={() => setOpen(false)} />
      </aside>
      {open && <div className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden" onClick={() => setOpen(false)} />}
      <Topbar onMenu={() => setOpen(true)} />
      <main className="mx-auto max-w-6xl p-4 sm:p-6"><Outlet /></main>
    </div>
  );
}

export default function AppLayout() {
  return <NewsPollProvider><Shell /></NewsPollProvider>;
}
