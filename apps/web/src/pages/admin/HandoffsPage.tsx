import { useState } from "react";
import { Link } from "react-router-dom";
import { useHandoffsList, useUpdateHandoff } from "../../hooks/useAdmin";
import type { HandoffStatus } from "../../api/admin";
import { ADMIN_PAGE_SIZE } from "../../api/admin";

const STATUSES: { value: string; label: string }[] = [
  { value: "open", label: "Abertos" },
  { value: "contacted", label: "Contactados" },
  { value: "closed", label: "Fechados" },
  { value: "all", label: "Todos" },
];

const STATUS_LABELS: Record<string, string> = { open: "Aberto", contacted: "Contactado", closed: "Fechado" };

const STATUS_BADGE: Record<string, string> = {
  open: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  contacted: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  closed: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
};

export default function HandoffsPage() {
  const [statusFilter, setStatusFilter] = useState("open");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useHandoffsList({
    status: statusFilter,
    page,
    size: ADMIN_PAGE_SIZE,
  });
  const update = useUpdateHandoff();

  const items = data?.items ?? [];

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Solicitações de atendimento</h2>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
        >
          {STATUSES.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
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
          {statusFilter === "open"
            ? "Nenhuma solicitação em aberto."
            : statusFilter === "contacted"
              ? "Nenhuma solicitação contactada."
              : statusFilter === "closed"
                ? "Nenhuma solicitação fechada."
                : "Nenhuma solicitação encontrada."}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-gray-600 dark:border-gray-700 dark:text-gray-400">
                <th className="pb-2 pr-4 font-medium">Usuário</th>
                <th className="pb-2 pr-4 font-medium">Conversa</th>
                <th className="pb-2 pr-4 font-medium">Status</th>
                <th className="pb-2 pr-4 font-medium">Data</th>
                <th className="pb-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-gray-100 dark:border-gray-800">
                  <td className="py-3 pr-4 text-gray-900 dark:text-gray-100">{item.user_email ?? "—"}</td>
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
                  <td className="py-3 pr-4">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_BADGE[item.status] ?? ""}`}>
                      {STATUS_LABELS[item.status] ?? item.status}
                    </span>
                  </td>
                  <td className="py-3 pr-4 text-gray-500 dark:text-gray-400">
                    {new Date(item.created_at).toLocaleDateString("pt-BR")}
                  </td>
                  <td className="py-3 text-right">
                    {item.status === "open" && (
                      <button
                        onClick={() => update.mutate({ id: item.id, body: { status: "contacted" as HandoffStatus } })}
                        className="mr-2 text-blue-600 hover:underline dark:text-blue-400"
                        disabled={update.isPending}
                      >
                        Marcar contactado
                      </button>
                    )}
                    {item.status !== "closed" && (
                      <button
                        onClick={() => update.mutate({ id: item.id, body: { status: "closed" as HandoffStatus } })}
                        className="text-green-600 hover:underline dark:text-green-400"
                        disabled={update.isPending}
                      >
                        Fechar
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
