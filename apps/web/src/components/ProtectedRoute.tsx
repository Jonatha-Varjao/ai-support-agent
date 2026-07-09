import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../features/auth/store";
import Spinner from "./Spinner";

export default function ProtectedRoute() {
  const { user, authStatus } = useAuthStore();

  if (authStatus !== "ready") {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Spinner />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}
