export default function Spinner({ size = "md" }: { size?: "sm" | "md" }) {
  const cls = size === "sm" ? "h-5 w-5" : "h-6 w-6";
  return <div className={`${cls} animate-spin rounded-full border-2 border-gray-300 border-t-blue-600`} />;
}
