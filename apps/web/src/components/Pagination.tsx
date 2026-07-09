interface Props {
  page: number;
  itemCount: number;
  pageSize: number;
  total?: number;
  onPageChange: (page: number) => void;
}

export default function Pagination({ page, itemCount, pageSize, total, onPageChange }: Props) {
  const hasNext = total !== undefined
    ? page < Math.ceil(total / pageSize)
    : itemCount >= pageSize;

  if (page <= 1 && !hasNext) return null;

  return (
    <div className="mt-4 flex justify-center gap-2">
      <button
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        className="rounded-lg border border-gray-300 px-3 py-1 text-sm disabled:opacity-40 dark:border-gray-600 dark:text-gray-300"
      >
        Anterior
      </button>
      <span className="px-2 py-1 text-sm text-gray-500">{page}</span>
      <button
        disabled={!hasNext}
        onClick={() => onPageChange(page + 1)}
        className="rounded-lg border border-gray-300 px-3 py-1 text-sm disabled:opacity-40 dark:border-gray-600 dark:text-gray-300"
      >
        Próximo
      </button>
    </div>
  );
}
