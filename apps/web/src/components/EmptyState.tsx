export default function EmptyState({ message }: { message: string }) {
  return (
    <div className="py-12 text-center text-sm text-gray-500 dark:text-gray-400">
      {message}
    </div>
  );
}
