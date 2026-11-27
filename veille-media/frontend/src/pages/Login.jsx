import { Newspaper } from "lucide-react";
import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Spinner } from "../components/ui";
import { useAuth } from "../contexts/AuthContext";
import { errorMessage } from "../services/api";

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to={location.state?.from?.pathname || "/"} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError("");
    try { await login(email, password); navigate(location.state?.from?.pathname || "/", { replace: true }); }
    catch (err) { setError(errorMessage(err, "Connexion impossible")); }
    finally { setBusy(false); }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4 p-6">
        <div className="text-center">
          <Newspaper className="mx-auto h-8 w-8 text-brand-600" />
          <h1 className="mt-2 text-xl font-semibold">Veille Média</h1>
          <p className="text-sm text-slate-500">Connectez-vous à votre espace</p>
        </div>
        <label className="block"><span className="label">E-mail</span>
          <input className="input" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="block"><span className="label">Mot de passe</span>
          <input className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <p role="alert" className="rounded-lg bg-red-50 p-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{error}</p>}
        <button className="btn-primary w-full justify-center" disabled={busy}>{busy && <Spinner className="!text-white" />} Se connecter</button>
      </form>
    </div>
  );
}
