"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, mediaUrl } from "@/lib/api";
import { formatAmount } from "@/lib/currency";
import { CATEGORIES, CATEGORY_COLOR_CLASS } from "@/lib/expenseCategories";
import AssistantChat from "@/components/AssistantChat";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import Spinner from "@/components/Spinner";
import StatusChip from "@/components/StatusChip";

const STATUS_PRIORITY = { overdue: 0, due_soon: 1, ok: 2 };
// More than the old car-list-first layout showed (3) — reminders are the
// section this redesign promotes, so there's now room for a couple more
// before "See all" takes over (see #63).
const UPCOMING_COUNT = 5;

// A single-month glance, not the multi-month bar chart — that lives on the
// dedicated Expenses page (see #63). `month` is the one row returned by
// ?months=1, i.e. the current month's totals.
function ThisMonthSpending({ month, currency }) {
  if (!month) return null;

  return (
    <div className="card">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-[13px] font-semibold">This month</p>
        <p className="text-xl font-bold">{formatAmount(month.total, currency)}</p>
      </div>
      {month.change_percent_vs_previous_month !== null && month.change_percent_vs_previous_month !== undefined && (
        <p className={`mb-2 text-[12px] font-medium ${month.change_percent_vs_previous_month > 0 ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"}`}>
          {month.change_percent_vs_previous_month > 0 ? "▲" : "▼"} {Math.abs(month.change_percent_vs_previous_month)}% vs last month
        </p>
      )}
      {month.total === 0 ? (
        <p className="text-[12px] text-gray-400 dark:text-gray-500">No expenses logged.</p>
      ) : (
        <div className="space-y-1.5">
          {CATEGORIES.filter(([key]) => (month.by_category?.[key] || 0) > 0).map(([key, label]) => (
            <div key={key} className="flex items-center justify-between text-[12px]">
              <span className="flex items-center gap-1.5 text-gray-600 dark:text-gray-300">
                <span className={`h-2 w-2 rounded-full ${CATEGORY_COLOR_CLASS[key]}`} />
                {label}
              </span>
              <span className="font-medium text-gray-900 dark:text-gray-100">
                {formatAmount(month.by_category[key], currency)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Dashboard() {
  const [cars, setCars] = useState(null);
  const [reminders, setReminders] = useState(null);
  const [remindersError, setRemindersError] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [analyticsError, setAnalyticsError] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/cars/")
      .then((data) => setCars(data.results || data))
      .catch((err) => setError(err.message));
    api("/reminders/")
      .then((data) => setReminders(data.results || data))
      .catch(() => setRemindersError(true));
    // Just the current month (see #63) — a full year-on-year chart belongs
    // on the dedicated Expenses page ("See details" below), not a
    // quick-glance dashboard tile.
    api("/expenses/analytics/?months=1")
      .then(setAnalytics)
      .catch(() => setAnalyticsError(true));
  }, []);

  const carById = Object.fromEntries((cars || []).map((car) => [car.id, car]));
  const upcoming = [...(reminders || [])]
    .sort((a, b) => (STATUS_PRIORITY[a.status] ?? 99) - (STATUS_PRIORITY[b.status] ?? 99))
    .slice(0, UPCOMING_COUNT);

  return (
    <main className="px-4 pb-32 pt-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold">Your Garage</h1>
      </header>

      {error && <p className="mb-4 rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p>}

      {cars === null && !error && <div className="flex justify-center py-6"><Spinner /></div>}

      {cars?.length === 0 && (
        <div className="card text-center">
          <div className="text-3xl">🅿️</div>
          <p className="mt-2 font-semibold">No cars yet</p>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Add your first car to start tracking services and expenses.</p>
        </div>
      )}

      {/* Compact picker (see #63) — cars are still one tap away, but no
          longer the dominant thing on the screen; that's now reminders and
          spending, the two things worth checking on every open. The
          assistant shares this row too (compact trigger, same chip size)
          instead of its own full-width card above it. */}
      {cars?.length > 0 && (
        <div className="flex gap-3 overflow-x-auto pb-1">
          <AssistantChat compact />
          {cars.map((car) => (
            <Link
              key={car.id}
              href={`/cars/${car.id}`}
              className="group flex w-16 flex-shrink-0 flex-col items-center gap-1.5 text-center outline-none active:scale-95"
            >
              {car.photo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={mediaUrl(car.photo_url)}
                  alt={`${car.make} ${car.model}`}
                  className="h-14 w-14 rounded-full border border-gray-200 object-cover transition group-focus-visible:ring-2 group-focus-visible:ring-brand dark:border-gray-800"
                />
              ) : (
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-gray-100 to-gray-200 text-2xl transition group-focus-visible:ring-2 group-focus-visible:ring-brand dark:from-gray-800 dark:to-gray-700">
                  🚗
                </div>
              )}
              <p className="w-full truncate text-[11px] font-medium text-gray-600 dark:text-gray-300">{car.model}</p>
            </Link>
          ))}
        </div>
      )}

      {cars?.length > 0 && (
        <div className="mt-6">
          <div className="mb-2 flex items-center justify-between">
            <p className="font-semibold">Upcoming</p>
            <Link href="/reminders" className="text-[13px] font-medium text-gray-500 dark:text-gray-400">See all</Link>
          </div>

          {reminders === null && !remindersError ? (
            <div className="flex justify-center py-4"><Spinner /></div>
          ) : remindersError ? (
            <p className="card text-center text-sm text-gray-500 dark:text-gray-400">Couldn&apos;t load reminders right now.</p>
          ) : upcoming.length === 0 ? (
            <Link href="/reminders/new" className="card block text-center text-sm text-gray-500 dark:text-gray-400">
              No reminders yet — add one to stay on top of maintenance.
            </Link>
          ) : (
            <div className="space-y-2">
              {upcoming.map((reminder) => (
                <Link
                  key={reminder.id}
                  href={`/reminders/${reminder.id}/edit`}
                  className="card flex items-center justify-between gap-3 py-3"
                >
                  <div className="min-w-0">
                    <p className="truncate font-semibold">{reminder.title}</p>
                    <p className="truncate text-[13px] text-gray-500 dark:text-gray-400">
                      {carById[reminder.car] ? `${carById[reminder.car].make} ${carById[reminder.car].model} · ` : ""}
                      {reminder.message}
                    </p>
                  </div>
                  <StatusChip status={reminder.status} />
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

      {cars?.length > 0 && (
        <div className="mt-6">
          <div className="mb-2 flex items-center justify-between">
            <p className="font-semibold">Spending</p>
            <Link href="/expenses" className="text-[13px] font-medium text-gray-500 dark:text-gray-400">See details</Link>
          </div>

          {analytics === null && !analyticsError ? (
            <div className="flex justify-center py-4"><Spinner /></div>
          ) : analyticsError ? (
            <p className="card text-center text-sm text-gray-500 dark:text-gray-400">Couldn&apos;t load spending right now.</p>
          ) : (
            <ThisMonthSpending month={analytics.months?.[0]} currency={analytics.currency} />
          )}
        </div>
      )}

      {/* bottom-24 is sized to clear BottomNav's floating pill (bottom-4 + its own
          height) — if that nav's height or offset changes, update this too. */}
      <div className="pointer-events-none fixed inset-x-0 bottom-24 z-30 mx-auto flex w-full max-w-lg justify-end px-4">
        <Link
          href="/cars/new"
          aria-label="Add a car"
          className="pointer-events-auto flex h-14 w-14 items-center justify-center rounded-full bg-gray-900 text-2xl text-white shadow-lg active:scale-95 dark:bg-white dark:text-gray-900"
        >
          +
        </Link>
      </div>

      <BottomNav />
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <Dashboard />
    </AuthGuard>
  );
}
