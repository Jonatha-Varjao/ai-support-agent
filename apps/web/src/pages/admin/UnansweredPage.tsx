import { useState } from "react";
import { Link } from "react-router-dom";
import { useUnansweredList, useUpdateUnanswered } from "../../hooks/useAdmin";
import { ADMIN_PAGE_SIZE } from "../../api/admin";

export default function UnansweredPage() {
  const [resolvedFilter, setResolvedFilter] = useState<string>("false");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useUnansweredList({
    resolved: resolvedFilter === "all" ? undefined : resolvedFilter === "true",
    page,
    size: ADMIN_PAGE_SIZE,
  });
  const resolve = useUpdateUnanswered();

  const handleResolve = (id: string) => resolve.mutate({ id, body: { resolved: true } });

  const items = data?.items ?? [];

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Perguntas não respondidas</h2>
        <select
          value={resolvedFilter}
          onChange={(e) => { setResolvedFilter(e.target.value); setPage(1); }}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
        >
          <option value="false">Não resolvidas</option>
          <option value="true">Resolvidas</option>
          <option value="all">Todas</option>
        </select>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-10 animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="py-12 text-center text-sm text-gray-500 dark:text-gray-400">
          {resolvedFilter === "false"
            ? "Nenhuma pergunta não respondida."
            : resolvedFilter === "true"
              ? "Nenhuma pergunta resolvida."
              : "Nenhuma pergunta encontrada."}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-gray-600 dark:border-gray-700 dark:text-gray-400">
                <th className="pb-2 pr-4 font-medium">Pergunta</th>
                <th className="pb-2 pr-4 font-medium">Similaridade</th>
                <th className="pb-2 pr-4 font-medium">Motivo</th>
                <th className="pb-2 pr-4 font-medium">Conversa</th>
                <th className="pb-2 pr-4 font-medium">Data</th>
                <th className="pb-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-gray-100 dark:border-gray-800">
                  <td className="max-w-xs truncate py-3 pr-4 text-gray-900 dark:text-gray-100">{item.query}</td>
                  <td className="py-3 pr-4">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${
                      item.top_sim >= 0.5 ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                        : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                    }`}>
                      {item.top_sim.toFixed(2)}
                    </span>
                  </td>
                  <td className="py-3 pr-4">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${
                      item.reason === "injection"
                        ? "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400"
                        : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                    }`}>
                      {item.reason === "injection" ? "Injeção" : "Sem contexto"}
                    </span>
                  </td>
                  <td className="py-3 pr-4">
                    {item.thread_title ? (
                      <Link to={`/c/${item.thread_id}`} className="text-blue-600 hover:underline dark:text-blue-400">
                        {item.thread_title}
                      </Link>
                    ) : (
                      <Link to={`/c/${item.thread_id}`} className="text-blue-600 hover:underline dark:text-blue-400">
                        Ver conversa
                      </Link>
                    )}
                  </td>
                  <td className="py-3 pr-4 text-gray-500 dark:text-gray-400">
                    {new Date(item.created_at).toLocaleDateString("pt-BR")}
                  </td>
                  <td className="py-3 text-right">
                    {!item.resolved && (
                      <button
                        onClick={() => handleResolve(item.id)}
                        className="text-blue-600 hover:underline dark:text-blue-400"
                        disabled={resolve.isPending}
                      >
                        Marcar como resolvida
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="mt-4 flex justify-center gap-2">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="rounded-lg border border-gray-300 px-3 py-1 text-sm disabled:opacity-40 dark:border-gray-600 dark:text-gray-300">
              Anterior
            </button>
            <span className="px-2 py-1 text-sm text-gray-500">{page}</span>
            <button disabled={items.length < ADMIN_PAGE_SIZE} onClick={() => setPage((p) => p + 1)} className="rounded-lg border border-gray-300 px-3 py-1 text-sm disabled:opacity-40 dark:border-gray-600 dark:text-gray-300">
              Próximo
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
