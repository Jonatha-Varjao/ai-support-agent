interface Props {
  count?: number;
  className?: string;
}

export default function Skeleton({ count = 4, className = "h-10" }: Props) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className={`animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700 ${className}`} />
      ))}
    </div>
  );
}
