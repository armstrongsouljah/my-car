"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { formatAmount } from "@/lib/currency";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import MonthChart, { monthLabel } from "@/components/MonthChart";

function Expenses() {
  const currentYear = new Date().getFullYear();

  const [cars, setCars] = useState([]);
  const [carFilter, setCarFilter] = useState("");
  const [yearFilter, setYearFilter] = useState(currentYear);
  const [analytics, setAnalytics] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    const carScope = carFilter ? `car=${carFilter}&` : "";
    // Explicit ?year= (see #58): a calendar year, not a rolling
    // trailing-12-months window that could span two different years.
    // yearFilter lets the owner browse past years (and, further back, an
    // all-time report — see the Reports page) rather than only ever seeing
    // the current one.
    // Guards against out-of-order responses: rapid ‹/› clicks fire a new
    // request per year before the previous one settles, and network timing
    // doesn't guarantee they resolve in the order they were sent.
    let cancelled = false;
    api(`/expenses/analytics/?${carScope}year=${yearFilter}`)
      .then((data) => { if (!cancelled) { setAnalytics(data); setError(""); } })
      .catch((err) => { if (!cancelled) setError(err.message); });
    return () => { cancelled = true; };
  }, [carFilter, yearFilter]);

  useEffect(() => {
    api("/cars/").then((data) => setCars(data.results || data)).catch(() => {});
  }, []);

  useEffect(() => load(), [load]);

  const isCurrentYear = yearFilter === currentYear;
  const latest = analytics?.months?.[analytics.months.length - 1];

  return (
    <main className="px-4 pb-24 pt-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Expenses</h1>
        <Link href="/expenses/reports" className="text-sm font-medium text-gray-500 dark:text-gray-400">
          Monthly reports ›
        </Link>
      </div>

      {error && <p className="mb-4 rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p>}

      <select className="input mb-4" value={carFilter} onChange={(e) => setCarFilter(e.target.value)}>
        <option value="">All cars</option>
        {cars.map((car) => (
          <option key={car.id} value={car.id}>{car.make} {car.model} {car.registration_number ? `— ${car.registration_number}` : ""}</option>
        ))}
      </select>

      {latest && (
        <div className="mb-4 grid grid-cols-2 gap-3">
          <div className="card">
            <p className="text-[12px] text-gray-400 dark:text-gray-500">{isCurrentYear ? "This month" : monthLabel(latest.month)}</p>
            <p className="text-xl font-bold">{formatAmount(latest.total, analytics.currency)}</p>
            {latest.change_percent_vs_previous_month !== null && latest.change_percent_vs_previous_month !== undefined && (
              <p className={`text-[12px] font-medium ${latest.change_percent_vs_previous_month > 0 ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"}`}>
                {latest.change_percent_vs_previous_month > 0 ? "▲" : "▼"} {Math.abs(latest.change_percent_vs_previous_month)}% vs last month
              </p>
            )}
          </div>
          <div className="card">
            <p className="text-[12px] text-gray-400 dark:text-gray-500">{isCurrentYear ? "Year to Date" : `${yearFilter} Total`}</p>
            <p className="text-xl font-bold">{formatAmount(analytics.grand_total, analytics.currency)}</p>
          </div>
        </div>
      )}

      <div className="mb-4">
        <MonthChart
          months={analytics?.months}
          currency={analytics?.currency}
          year={yearFilter}
          onPrevYear={() => setYearFilter((y) => y - 1)}
          onNextYear={() => setYearFilter((y) => y + 1)}
          // No floor — the backend (see #60) already only shows a
          // pre-join-date month when it has real data, zero-filling
          // nothing before signup, so there's nothing to protect the
          // owner from by blocking navigation itself. A genuinely empty
          // year still falls through to the "no expenses logged" state
          // below (#116).
          canGoPrev
          canGoNext={yearFilter < currentYear}
        />
      </div>

      {/* Analytics only here (see #120) — the raw expense log has its own
          page now, reached via "View all" below, same pattern as the
          dashboard's "Spending" summary linking out to this page. */}
      {cars.length === 0 ? (
        <button className="btn-secondary mb-3" disabled>+ Log an expense</button>
      ) : (
        <Link href="/expenses/new" className="btn-secondary mb-3 inline-block text-center">
          + Log an expense
        </Link>
      )}

      <Link href="/expenses/list" className="block text-center text-sm font-medium text-gray-500 dark:text-gray-400">
        View all expenses ›
      </Link>

      <BottomNav />
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <Expenses />
    </AuthGuard>
  );
}
