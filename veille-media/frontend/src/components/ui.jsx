import { AlertTriangle, Loader2, X } from "lucide-react";

export const Spinner = ({ className = "" }) => <Loader2 className={`h-5 w-5 animate-spin text-brand-500 ${className}`} />;

export const Loading = () => <div className="flex justify-center py-16"><Spinner className="h-7 w-7" /></div>;

export const ErrorBox = ({ message, onRetry }) => (
  <div className="card flex items-center gap-3 border-red-200 p-4 text-sm text-red-700 dark:border-red-900 dark:text-red-300">
    <AlertTriangle className="h-5 w-5 shrink-0" />
    <span className="flex-1">{message}</span>
    {onRetry && <button className="btn-outline" onClick={onRetry}>Réessayer</button>}
  </div>
);

export const EmptyState = ({ title, hint }) => (
  <div className="card p-10 text-center">
    <p className="font-medium">{title}</p>
    {hint && <p className="mt-1 text-sm text-slate-500">{hint}</p>}
  </div>
);

export const PageTitle = ({ title, subtitle, actions }) => (
  <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
    <div>
      <h1 className="text-xl font-semibold">{title}</h1>
      {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
    </div>
    <div className="flex flex-wrap gap-2">{actions}</div>
  </div>
);

export function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4" onMouseDown={onClose}>
      <div className="card max-h-[90vh] w-full max-w-lg overflow-y-auto p-5" onMouseDown={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-semibold">{title}</h2>
          <button className="btn-ghost !p-1" onClick={onClose} aria-label="Fermer"><X className="h-5 w-5" /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

export const Field = ({ label, children }) => (
  <label className="block"><span className="label">{label}</span>{children}</label>
);

const STATUS = {
  idle: ["Active", "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"],
  collecting: ["En cours de collecte", "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300"],
  error: ["Erreur", "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"],
  inactive: ["Désactivée", "bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400"],
  success: ["Succès", "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"],
  partial: ["Partiel", "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300"],
  running: ["En cours", "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300"],
};

export function StatusBadge({ status, active = true }) {
  const key = active === false ? "inactive" : status;
  const [label, cls] = STATUS[key] || [status, STATUS.inactive[1]];
  return <span className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{label}</span>;
}
