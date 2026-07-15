export default function StatusChip({ status }) {
  const styles = {
    overdue: "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400",
    due_soon: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400",
    ok: "bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400",
  };
  const labels = { overdue: "Overdue", due_soon: "Due soon", ok: "OK" };
  return <span className={`chip ${styles[status] || styles.ok}`}>{labels[status] || status}</span>;
}
