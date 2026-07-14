export default function StatusChip({ status }) {
  const styles = {
    overdue: "bg-red-100 text-red-700",
    due_soon: "bg-amber-100 text-amber-700",
    ok: "bg-green-100 text-green-700",
  };
  const labels = { overdue: "Overdue", due_soon: "Due soon", ok: "OK" };
  return <span className={`chip ${styles[status] || styles.ok}`}>{labels[status] || status}</span>;
}
