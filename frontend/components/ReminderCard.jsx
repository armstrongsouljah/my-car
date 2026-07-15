import Link from "next/link";
import ProgressBar from "@/components/ProgressBar";
import StatusChip from "@/components/StatusChip";

function rangeLabel(reminder) {
  if (reminder.baseline_odometer_km != null && reminder.next_due_odometer_km != null) {
    return [`${Number(reminder.baseline_odometer_km).toLocaleString()} km`, `${Number(reminder.next_due_odometer_km).toLocaleString()} km`];
  }
  if (reminder.baseline_date && reminder.next_due_date) {
    return [reminder.baseline_date, reminder.next_due_date];
  }
  return null;
}

export default function ReminderCard({ reminder }) {
  const range = rangeLabel(reminder);

  return (
    <Link href={`/reminders/${reminder.id}/edit`} className="card block">
      <div className="flex items-start justify-between gap-3">
        <div>
          {reminder.is_essential && <p className="text-[12px] font-semibold text-blue-600 dark:text-blue-400">Essential</p>}
          <p className="font-semibold">{reminder.title}</p>
        </div>
        <StatusChip status={reminder.status} />
      </div>
      <p className="mt-1 text-[13px] text-gray-500 dark:text-gray-400">{reminder.message}</p>
      <div className="mt-2">
        <ProgressBar percent={reminder.progress_percent} status={reminder.status} />
        {range && (
          <div className="mt-1 flex justify-between text-[12px] text-gray-400 dark:text-gray-500">
            <span>{range[0]}</span>
            <span>{range[1]}</span>
          </div>
        )}
      </div>
    </Link>
  );
}
