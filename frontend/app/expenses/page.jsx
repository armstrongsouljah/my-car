"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { formatAmount } from "@/lib/currency";
import { CATEGORY_LABELS } from "@/lib/expenseCategories";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import FilterChips from "@/components/FilterChips";
import MonthChart, { monthLabel } from "@/components/MonthChart";

const PERIODS = [
  { value: "week", label: "This week" },
  { value: "month", label: "This month" },
  { value: "year", label: "This year" },
];

function Expenses() {
  const currentYear = new Date().getFullYear();

  const [cars, setCars] = useState([]);
  const [carFilter, setCarFilter] = useState("");
  // Independent of yearFilter/analytics below — this only scopes the log
  // list, not the month-on-month cards/chart above it (see #25).
  const [periodFilter, setPeriodFilter] = useState("week");
  const [yearFilter, setYearFilter] = useState(currentYear);
  const [analytics, setAnalytics] = useState(null);
  const [expenses, setExpenses] = useState([]);
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
    api(`/expenses/?${carScope}period=${periodFilter}`)
      .then((data) => { if (!cancelled) setExpenses(data.results || data); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [carFilter, periodFilter, yearFilter]);

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
          // No floor — imported historical service history (#103) can
          // predate when the owner actually joined, so year-browsing isn't
          // clamped to that anymore. A genuinely empty year just shows the
          // existing "no expenses logged" state below.
          canGoPrev
          canGoNext={yearFilter < currentYear}
        />
      </div>

      {cars.length === 0 ? (
        <button className="btn-secondary mb-4" disabled>+ Log an expense</button>
      ) : (
        <Link href="/expenses/new" className="btn-secondary mb-4 inline-block text-center">
          + Log an expense
        </Link>
      )}

      <div className="mt-6 mb-2">
        <p className="mb-2 text-[13px] font-semibold text-gray-500 dark:text-gray-400">Expense log</p>
        <FilterChips options={PERIODS} value={periodFilter} onChange={setPeriodFilter} />
      </div>

      {/* Fixed-height + its own scroll container instead of letting the list
          push the rest of the page down as more expenses get logged (#25). */}
      <div className="max-h-[60vh] space-y-3 overflow-y-auto pb-1">
        {expenses.map((expense) => (
          <Link
            key={expense.id}
            href={`/expenses/${expense.id}`}
            className="card flex items-center justify-between text-sm active:scale-[0.99]"
          >
            <div className="min-w-0">
              <p className="font-semibold">{CATEGORY_LABELS[expense.category] || expense.category}</p>
              <p className="text-gray-500 dark:text-gray-400">
                {expense.expense_date}
                {expense.vendor ? ` · ${expense.vendor}` : ""}
                {expense.litres ? ` · ${expense.litres} L` : ""}
              </p>
              {expense.description && (
                <p className="mt-0.5 truncate text-[13px] text-gray-400 dark:text-gray-500">{expense.description}</p>
              )}
            </div>
            <div className="flex flex-shrink-0 items-center gap-2">
              <p className="font-bold">{formatAmount(expense.display_amount, expense.display_currency)}</p>
              <span className="text-gray-300 dark:text-gray-600">›</span>
            </div>
          </Link>
        ))}
        {expenses.length === 0 && (
          <p className="text-center text-sm text-gray-400 dark:text-gray-500">
            No expenses logged {periodFilter === "week" ? "this week" : periodFilter === "month" ? "this month" : "this year"}.
          </p>
        )}
      </div>

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
