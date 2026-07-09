import { NavLink, Outlet, Link } from "react-router-dom";

const LINKS = [
  { to: "/admin/kb", label: "Base de conhecimento" },
  { to: "/admin/unanswered", label: "Não respondidas" },
  { to: "/admin/handoffs", label: "Handoffs" },
  { to: "/admin/threads", label: "Conversas" },
];

export default function AdminLayout() {
  return (
    <div className="flex h-screen flex-col bg-white dark:bg-gray-900">
      <header className="border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between px-4 py-3 sm:px-6">
          <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Admin</h1>
          <Link
            to="/"
            className="text-sm text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
          >
            ← Voltar ao chat
          </Link>
        </div>
        <nav className="flex flex-wrap gap-1 border-t border-gray-200 px-4 py-2 sm:px-6 dark:border-gray-700">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end
              className={({ isActive }) =>
                `rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-gray-200 text-gray-900 dark:bg-gray-700 dark:text-gray-100"
                    : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700/50"
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <Outlet />
      </div>
    </div>
  );
}
