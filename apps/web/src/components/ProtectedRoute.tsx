import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../features/auth/store";

export default function ProtectedRoute() {
  const { user, authStatus } = useAuthStore();

  if (authStatus !== "ready") {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}
