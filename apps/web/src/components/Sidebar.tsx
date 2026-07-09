import { useState, useRef, useEffect } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { useAuthStore } from "../features/auth/store";
import { useThreads, useRenameThread, useDeleteThread } from "../hooks/useChatThreads";
import UserMenu from "./UserMenu";
import Skeleton from "./Skeleton";

export default function Sidebar() {
  const { data: threads, isLoading } = useThreads();
  const rename = useRenameThread();
  const del = useDeleteThread();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const user = useAuthStore((s) => s.user);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editingId) inputRef.current?.focus();
  }, [editingId]);

  const handleNew = () => navigate("/");

  const handleSelect = (id: string) => {
    if (editingId) return;
    navigate(`/c/${id}`);
  };

  const startEdit = (id: string, title: string) => {
    setEditingId(id);
    setEditTitle(title);
  };

  const saveEdit = async () => {
    if (!editingId || !editTitle.trim()) {
      setEditingId(null);
      return;
    }
    try {
      await rename.mutateAsync({ id: editingId, title: editTitle.trim() });
    } catch {
      // ignore — data will be invalidated on refetch
    }
    setEditingId(null);
  };

  const handleDelete = (id: string) => {
    if (!window.confirm("Excluir esta conversa?")) return;
    del.mutate(id);
  };

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") saveEdit();
    if (e.key === "Escape") setEditingId(null);
  };

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
      <div className="p-3">
        {user?.role === "admin" && (
          <Link
            to="/admin/kb"
            className={`mb-2 flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              pathname.startsWith("/admin")
                ? "bg-gray-200 text-gray-900 dark:bg-gray-700 dark:text-gray-100"
                : "text-gray-700 hover:bg-gray-200 dark:text-gray-300 dark:hover:bg-gray-700"
            }`}
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            Admin
          </Link>
        )}
        <button
          onClick={handleNew}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-200 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Nova conversa
        </button>
      </div>

      {isLoading ? (
        <nav className="flex-1 overflow-y-auto px-2">
          <Skeleton count={3} className="h-9 mb-1" />
        </nav>
      ) : (
        <nav className="flex-1 overflow-y-auto px-2">
          {threads?.map((t) => (
            <div key={t.id} className="group relative mb-1">
              {editingId === t.id ? (
                <input
                  ref={inputRef}
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onBlur={saveEdit}
                  onKeyDown={handleEditKeyDown}
                  maxLength={100}
                  className="w-full rounded-lg border border-blue-400 px-3 py-2.5 text-left text-sm text-gray-900 outline-none dark:border-blue-500 dark:bg-gray-700 dark:text-gray-100"
                />
              ) : (
                <button
                  onClick={() => handleSelect(t.id)}
                  className={`w-full truncate rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${
                    pathname === `/c/${t.id}`
                      ? "bg-gray-200 text-gray-900 dark:bg-gray-700 dark:text-gray-100"
                      : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700/50"
                  }`}
                >
                  {t.title}
                </button>
              )}

              {editingId !== t.id && (
                <div className="absolute right-1 top-1/2 hidden -translate-y-1/2 gap-0.5 group-hover:flex">
                  <button
                    onClick={(e) => { e.stopPropagation(); startEdit(t.id, t.title); }}
                    className="rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
                    title="Renomear"
                  >
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(t.id); }}
                    className="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-500 dark:hover:bg-red-900/30 dark:hover:text-red-400"
                    title="Excluir"
                  >
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              )}
            </div>
          ))}
        </nav>
      )}

      <div className="border-t border-gray-200 p-2 dark:border-gray-700">
        <UserMenu />
      </div>
    </aside>
  );
}
