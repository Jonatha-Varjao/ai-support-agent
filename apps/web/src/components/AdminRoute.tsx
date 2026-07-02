import { Navigate, Outlet, Link } from "react-router-dom";
import { useAuthStore } from "../features/auth/store";

export default function AdminRoute() {
  const { user, authStatus } = useAuthStore();

  if (authStatus !== "ready") {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  if (user.role !== "admin") {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">403</h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Acesso restrito a administradores.</p>
          <Link to="/" className="mt-3 inline-block text-sm text-blue-600 hover:underline dark:text-blue-400">
            Voltar ao chat
          </Link>
        </div>
      </div>
    );
  }

  return <Outlet />;
}
