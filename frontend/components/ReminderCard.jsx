"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import ConfirmDialog from "@/components/ConfirmDialog";
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

// `onCompleted` (see #128) -- until now the only way to move a reminder's
// baseline forward was editing it by hand on its own page. Card is a plain
// div (not itself a Link, unlike before) so the "Mark as done" button can
// sit alongside the title/progress area without nesting a <button> inside
// an <a> -- the title/progress area is its own inner Link instead.
//
// Restricted to overdue reminders and gated behind a confirmation (a
// follow-up to #134) -- this overwrites the baseline with no undo, and an
// unconfirmed button on every reminder regardless of status was too easy to
// tap by accident.
export default function ReminderCard({ reminder, onCompleted }) {
  const range = rangeLabel(reminder);
  const [completing, setCompleting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [error, setError] = useState("");

  async function markDone() {
    setError("");
    setCompleting(true);
    try {
      const updated = await api(`/reminders/${reminder.id}/complete/`, { method: "POST" });
      onCompleted?.(updated);
      setConfirmOpen(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setCompleting(false);
    }
  }

  return (
    <div className="card">
      <Link href={`/reminders/${reminder.id}/edit`} className="block">
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

      {error && <p className="mt-2 text-[12px] text-red-600 dark:text-red-400">{error}</p>}

      {reminder.status === "overdue" && (
        <button
          type="button"
          onClick={() => setConfirmOpen(true)}
          className="btn-chip mt-3 w-full justify-center"
        >
          ✓ Mark as done
        </button>
      )}

      <ConfirmDialog
        open={confirmOpen}
        loading={completing}
        title="Mark this reminder as done?"
        message={`"${reminder.title}" will be reset as if you just did it today -- this can't be undone.`}
        confirmLabel="Mark as done"
        cancelLabel="Cancel"
        onConfirm={markDone}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}
