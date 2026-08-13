"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import ConfirmDialog from "@/components/ConfirmDialog";
import ReminderDetailsForm from "@/components/ReminderDetailsForm";
import Spinner from "@/components/Spinner";

function EditReminder() {
  const { id } = useParams();
  const router = useRouter();
  const [reminder, setReminder] = useState(null);
  const [car, setCar] = useState(null);
  const [error, setError] = useState("");
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [confirmDone, setConfirmDone] = useState(false);
  const [completing, setCompleting] = useState(false);
  // ReminderDetailsForm seeds its own local state from `reminder` once on
  // mount (same pattern as ExpenseForm) -- bumping this forces a remount so
  // a reset baseline actually shows up in the form after markDone(), not
  // just in the read-only bits of this page.
  const [completedCount, setCompletedCount] = useState(0);

  const load = useCallback(() => {
    // Returned (not fire-and-forget) so markDone() below can await it --
    // otherwise the ReminderDetailsForm remount races the refetch and can
    // remount with the pre-completion baseline still in state.
    return api(`/reminders/${id}/`)
      .then((data) => {
        setReminder(data);
        return api(`/cars/${data.car}/`);
      })
      .then(setCar)
      .catch((err) => setError(err.message));
  }, [id]);

  useEffect(() => { load(); }, [load]);

  async function markDone() {
    setCompleting(true);
    try {
      await api(`/reminders/${id}/complete/`, { method: "POST" });
      await load(); // refetches so the remount below picks up the reset baseline, not the stale one
      setCompletedCount((count) => count + 1);
      setConfirmDone(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setCompleting(false);
    }
  }

  async function remove() {
    setRemoving(true);
    try {
      await api(`/reminders/${id}/`, { method: "DELETE" });
      router.replace("/reminders");
    } catch (err) {
      setError(err.message);
      setRemoving(false);
      setConfirmRemove(false);
    }
  }

  if (error) return <main className="p-6"><p className="rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p></main>;
  if (!reminder || !car) return <main className="flex justify-center p-10"><Spinner /></main>;

  return (
    <main className="px-4 pb-24 pt-6">
      <button onClick={() => router.back()} className="mb-4 text-sm text-gray-500 dark:text-gray-400">‹ Back</button>
      <h1 className="mb-4 text-2xl font-bold">{reminder.title}</h1>

      {/* Same restriction as ReminderCard.jsx (see #134 follow-up): only
          shown once actually overdue, and gated behind a confirmation --
          this overwrites the baseline with no undo. */}
      {reminder.status === "overdue" && (
        <button onClick={() => setConfirmDone(true)} className="btn-secondary mb-4">
          ✓ Mark as done today
        </button>
      )}

      <ReminderDetailsForm
        key={completedCount}
        car={car}
        reminder={reminder}
        editableMethod
        onSaved={() => router.replace("/reminders")}
        onCancel={() => router.back()}
      />

      <button
        onClick={() => setConfirmRemove(true)}
        className="mt-3 w-full rounded-xl border border-red-200 dark:border-red-500/30 bg-red-50 dark:bg-red-500/10 px-4 py-3 text-[15px] font-semibold text-red-600 dark:text-red-400"
      >
        Remove reminder
      </button>

      <ConfirmDialog
        open={confirmRemove}
        destructive
        loading={removing}
        title="Remove this reminder?"
        message={`"${reminder.title}" will be permanently removed.`}
        confirmLabel="Remove reminder"
        cancelLabel="Keep reminder"
        onConfirm={remove}
        onCancel={() => setConfirmRemove(false)}
      />

      <ConfirmDialog
        open={confirmDone}
        loading={completing}
        title="Mark this reminder as done?"
        message={`"${reminder.title}" will be reset as if you just did it today -- this can't be undone.`}
        confirmLabel="Mark as done"
        cancelLabel="Cancel"
        onConfirm={markDone}
        onCancel={() => setConfirmDone(false)}
      />

      <BottomNav />
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <EditReminder />
    </AuthGuard>
  );
}
