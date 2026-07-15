export default function ProgressBar({ percent, status }) {
  const fill = {
    overdue: "bg-red-500",
    due_soon: "bg-amber-500",
    ok: "bg-green-500",
  };
  const clamped = Math.max(0, Math.min(100, percent ?? 0));

  return (
    <div className="h-2 w-full rounded-full bg-gray-100 dark:bg-gray-800">
      <div
        className={`h-2 rounded-full ${fill[status] || fill.ok}`}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
