import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import AppLayout from "./layouts/AppLayout";
import Dashboard from "./pages/Dashboard";
import Feed from "./pages/Feed";
import Login from "./pages/Login";
import NewsDetail from "./pages/NewsDetail";
import AdminAgent from "./pages/admin/AdminAgent";
import AdminCategories from "./pages/admin/AdminCategories";
import AdminSources from "./pages/admin/AdminSources";
import AdminUsers from "./pages/admin/AdminUsers";

export default function App() {
  return (
    <Routes>
      <Route path="/connexion" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="actualites" element={<Feed mode="all" />} />
          <Route path="actualites/:id" element={<NewsDetail />} />
          <Route path="categorie/:group" element={<Feed mode="all" />} />
          <Route path="favoris" element={<Feed mode="favorites" />} />
          <Route path="historique" element={<Feed mode="history" />} />
          <Route element={<ProtectedRoute adminOnly />}>
            <Route path="admin/agent" element={<AdminAgent />} />
            <Route path="admin/sources" element={<AdminSources />} />
            <Route path="admin/categories" element={<AdminCategories />} />
            <Route path="admin/utilisateurs" element={<AdminUsers />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
