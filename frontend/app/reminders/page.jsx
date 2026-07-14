"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import StatusChip from "@/components/StatusChip";

function Reminders() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/services/reminders/").then(setData).catch((err) => setError(err.message));
  }, []);

  return (
    <main className="px-4 pb-24 pt-6">
      <h1 className="mb-6 text-2xl font-bold">Reminders</h1>

      {error && <p className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {data === null && !error && <p className="text-sm text-gray-400">Loading…</p>}
      {data?.length === 0 && (
        <div className="card text-center text-sm text-gray-500">Add a car to start getting service and inspection reminders.</div>
      )}

      <div className="space-y-4">
        {data?.map((entry) => (
          <div key={entry.car_id} className="card">
            <Link href={`/cars/${entry.car_id}`} className="flex items-center justify-between">
              <p className="font-semibold">{entry.car}</p>
              <span className="text-gray-300">›</span>
            </Link>
            <p className="mt-0.5 text-[13px] text-gray-400">{Number(entry.current_odometer_km).toLocaleString()} km</p>
            <div className="mt-3 space-y-2">
              {entry.reminders.map((reminder) => (
                <div key={reminder.kind} className="flex items-center justify-between gap-3 rounded-xl bg-gray-50 p-3">
                  <p className="text-[13px] text-gray-600">{reminder.message}</p>
                  <StatusChip status={reminder.status} />
                </div>
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
