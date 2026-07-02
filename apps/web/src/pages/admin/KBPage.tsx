import { useState } from "react";
import { useKBList, useKBCreate, useKBUpdate, useKBDelete } from "../../hooks/useAdmin";
import type { KBCreateRequest, KBUpdateRequest, KBListItem } from "../../api/admin";
import { KB_CATEGORIES, KB_CATEGORY_LABELS } from "../../api/admin";
import { ADMIN_PAGE_SIZE } from "../../api/admin";
import KBFormDrawer from "../../components/KBFormDrawer";

export default function KBPage() {
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState<KBListItem | null>(null);

  const { data, isLoading } = useKBList({ category: category || undefined, page, size: ADMIN_PAGE_SIZE });
  const create = useKBCreate();
  const update = useKBUpdate();
  const del = useKBDelete();

  const openCreate = () => { setEditingEntry(null); setDrawerOpen(true); };
  const openEdit = (e: KBListItem) => { setEditingEntry(e); setDrawerOpen(true); };
  const closeDrawer = () => setDrawerOpen(false);

  const handleSave = async (body: KBCreateRequest | KBUpdateRequest) => {
    if (editingEntry) {
      await update.mutateAsync({ id: editingEntry.id, body: body as KBUpdateRequest });
    } else {
      await create.mutateAsync(body as KBCreateRequest);
    }
  };

  const handleDelete = (id: string) => {
    if (!window.confirm("Excluir esta entrada?")) return;
    del.mutate(id);
  };

  const entries = data?.items ?? [];

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Base de conhecimento</h2>
          <select
            value={category}
            onChange={(e) => { setCategory(e.target.value); setPage(1); }}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
          >
            <option value="">Todas</option>
            {KB_CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>
        <button onClick={openCreate} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          Adicionar entrada
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="h-10 animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700" />
          ))}
        </div>
      ) : entries.length === 0 ? (
        <div className="py-12 text-center text-sm text-gray-500 dark:text-gray-400">
          Nenhuma entrada. Adicione a primeira.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-gray-600 dark:border-gray-700 dark:text-gray-400">
                <th className="pb-2 pr-4 font-medium">Título</th>
                <th className="pb-2 pr-4 font-medium">Categoria</th>
                <th className="pb-2 pr-4 font-medium">Atualizado</th>
                <th className="pb-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id} className="border-b border-gray-100 dark:border-gray-800">
                  <td className="max-w-xs truncate py-3 pr-4 text-gray-900 dark:text-gray-100">{e.title}</td>
                  <td className="py-3 pr-4">
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                      {KB_CATEGORY_LABELS[e.category] ?? e.category}
                    </span>
                  </td>
                  <td className="py-3 pr-4 text-gray-500 dark:text-gray-400">
                    {new Date(e.updated_at).toLocaleDateString("pt-BR")}
                  </td>
                  <td className="py-3 text-right">
                    <button onClick={() => openEdit(e)} className="mr-2 text-blue-600 hover:underline dark:text-blue-400">
                      Editar
                    </button>
                    <button onClick={() => handleDelete(e.id)} className="text-red-500 hover:underline">
                      Excluir
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {(page > 1 || entries.length >= ADMIN_PAGE_SIZE) && (
            <div className="mt-4 flex justify-center gap-2">
              <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="rounded-lg border border-gray-300 px-3 py-1 text-sm disabled:opacity-40 dark:border-gray-600 dark:text-gray-300">
                Anterior
              </button>
              <span className="px-2 py-1 text-sm text-gray-500">{page}</span>
              <button disabled={entries.length < ADMIN_PAGE_SIZE} onClick={() => setPage((p) => p + 1)} className="rounded-lg border border-gray-300 px-3 py-1 text-sm disabled:opacity-40 dark:border-gray-600 dark:text-gray-300">
                Próximo
              </button>
            </div>
          )}
        </div>
      )}

      <KBFormDrawer
        open={drawerOpen}
        onClose={closeDrawer}
        onSave={handleSave}
        initial={editingEntry}
        saving={create.isPending || update.isPending}
      />
    </div>
  );
}
