import { useState } from "react";
import { Link } from "react-router-dom";
import { useAdminThreads } from "../../hooks/useAdmin";
import { ADMIN_PAGE_SIZE } from "../../api/admin";
import Skeleton from "../../components/Skeleton";
import Pagination from "../../components/Pagination";
import EmptyState from "../../components/EmptyState";

export default function AdminThreadsPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useAdminThreads({ page, size: ADMIN_PAGE_SIZE });

  const items = data?.items ?? [];

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">Conversas</h2>
      {isLoading ? (
        <Skeleton />
      ) : items.length === 0 ? (
        <EmptyState message="Nenhuma conversa encontrada." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-gray-600 dark:border-gray-700 dark:text-gray-400">
                <th className="pb-2 pr-4 font-medium">Usuário</th>
                <th className="pb-2 pr-4 font-medium">Título</th>
                <th className="pb-2 pr-4 font-medium">Atualizado</th>
                <th className="pb-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {items.map((t) => (
                <tr key={t.id} className="border-b border-gray-100 dark:border-gray-800">
                  <td className="py-3 pr-4 text-gray-900 dark:text-gray-100">{t.user_email}</td>
                  <td className="max-w-xs truncate py-3 pr-4 text-gray-900 dark:text-gray-100">{t.title}</td>
                  <td className="py-3 pr-4 text-gray-500 dark:text-gray-400">
                    {new Date(t.updated_at).toLocaleDateString("pt-BR")}
                  </td>
                  <td className="py-3 text-right">
                    <Link to={`/admin/chat/${t.id}`} className="text-blue-600 hover:underline dark:text-blue-400">
                      Ver conversa
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={page} itemCount={items.length} pageSize={ADMIN_PAGE_SIZE} total={data?.total} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}
