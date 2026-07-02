import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import { useThemeStore } from "./features/theme/store";
import { useAuthStore } from "./features/auth/store";
import LoginPage from "./pages/LoginPage";
import ChatLayout from "./pages/ChatLayout";
import NewChatPage from "./pages/NewChatPage";
import ChatPage from "./pages/ChatPage";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";
import AdminLayout from "./components/AdminLayout";
import KBPage from "./pages/admin/KBPage";
import UnansweredPage from "./pages/admin/UnansweredPage";
import HandoffsPage from "./pages/admin/HandoffsPage";

export default function App() {
  const theme = useThemeStore((s) => s.theme);
  const authStatus = useAuthStore((s) => s.authStatus);
  const hydrate = useAuthStore((s) => s.hydrate);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    const onExpired = () => {
      useAuthStore.getState().logout();
    };
    window.addEventListener("auth:expired", onExpired);
    return () => window.removeEventListener("auth:expired", onExpired);
  }, []);

  if (authStatus !== "ready") {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<ChatLayout />}>
            <Route path="/" element={<NewChatPage />} />
            <Route path="/c/:threadId" element={<ChatPage />} />
          </Route>
        </Route>
        <Route element={<AdminRoute />}>
          <Route element={<AdminLayout />}>
            <Route path="/admin/kb" element={<KBPage />} />
            <Route path="/admin/unanswered" element={<UnansweredPage />} />
            <Route path="/admin/handoffs" element={<HandoffsPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
