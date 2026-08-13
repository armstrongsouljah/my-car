"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import ProgressBar from "@/components/ProgressBar";
import Spinner from "@/components/Spinner";
import StatusChip from "@/components/StatusChip";
import ReminderCard from "@/components/ReminderCard";

function carLabel(entry) {
  return `${entry.make} ${entry.model}${entry.year ? ` (${entry.year})` : ""}`;
}

function Reminders() {
  const [data, setData] = useState(null);
  const [reminders, setReminders] = useState({});
  const [error, setError] = useState("");

  useEffect(() => {
    api("/services/reminders/")
      .then((entries) => {
        setData(entries);
        return api("/reminders/");
      })
      .then((page) => {
        const results = page.results || page;
        const grouped = {};
        results.forEach((reminder) => {
          grouped[reminder.car] = grouped[reminder.car] || [];
          grouped[reminder.car].push(reminder);
        });
        setReminders(grouped);
      })
      .catch((err) => setError(err.message));
  }, []);

  // Patches a single reminder in place after it's marked done, rather than
  // refetching the whole grouped structure -- see ReminderCard's onCompleted.
  function updateReminder(updated) {
    setReminders((current) => {
      const next = { ...current };
      for (const carId of Object.keys(next)) {
        next[carId] = next[carId].map((reminder) => (reminder.id === updated.id ? updated : reminder));
      }
      return next;
    });
  }

  return (
    <main className="px-4 pb-24 pt-6">
      <h1 className="mb-6 text-2xl font-bold">Reminders</h1>

      {error && <p className="mb-4 rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p>}
      {data === null && !error && <div className="flex justify-center py-6"><Spinner /></div>}
      {data?.length === 0 && (
        <div className="card text-center text-sm text-gray-500 dark:text-gray-400">Add a car to start getting service and inspection reminders.</div>
      )}

      <div className="space-y-8">
        {data?.map((entry) => (
          <div key={entry.car_id}>
            <Link href={`/cars/${entry.car_id}`} className="mb-3 flex items-center justify-between">
              <div>
                <p className="font-semibold">{carLabel(entry)}</p>
                <p className="mt-0.5 text-[13px] text-gray-400 dark:text-gray-500">
                  {entry.registration_number ? (
                    <span className="select-none blur-[3px]">{entry.registration_number}</span>
                  ) : (
                    "No plate"
                  )}{" "}
                  · {Number(entry.current_odometer_km).toLocaleString()} km
                </p>
              </div>
              <span className="text-gray-300 dark:text-gray-600">›</span>
            </Link>

            <div className="space-y-3">
              {/* Above the list, not below it -- stays reachable regardless
                  of how many reminders this car already has, same fix as
                  the car detail page's "+ Log a service"/"+ Log an
                  inspection" placement (#112 dealt with the equivalent
                  push-down-the-page problem for those lists). */}
              <Link href={`/reminders/new?car=${entry.car_id}`} className="btn-secondary block text-center">
                + Add reminder
              </Link>

              {/* Flat .card rows directly here, not nested inside another
                  wrapping card -- matches how every other list page (car
                  detail's own service/inspection tabs, the expense log)
                  renders its items (#118). Catalog reminders previously used
                  a bare inset box instead of .card; brought in line with
                  ReminderCard (custom reminders) and with how the car detail
                  page already renders this same {kind, message, status}
                  shape for its own single-car reminders block. */}
              {entry.reminders.map((reminder) => (
                <div key={reminder.kind} className="card">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-[13px] font-semibold capitalize">{reminder.kind}</p>
                    <StatusChip status={reminder.status} />
                  </div>
                  <p className="mt-1 text-[13px] text-gray-500 dark:text-gray-400">{reminder.message}</p>
                  <div className="mt-2">
                    <ProgressBar percent={reminder.progress_percent} status={reminder.status} />
                  </div>
                </div>
              ))}

              {reminders[entry.car_id]?.map((reminder) => (
                <ReminderCard key={reminder.id} reminder={reminder} onCompleted={updateReminder} />
              ))}
            </div>
          </div>
        ))}
      </div>

      <BottomNav />
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <Reminders />
    </AuthGuard>
  );
}
