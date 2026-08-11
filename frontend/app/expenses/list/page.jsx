"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { formatAmount } from "@/lib/currency";
import { CATEGORY_LABELS } from "@/lib/expenseCategories";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import FilterChips from "@/components/FilterChips";
import Spinner from "@/components/Spinner";

const PERIODS = [
  { value: "week", label: "This week" },
  { value: "month", label: "This month" },
  { value: "year", label: "This year" },
];

function ExpenseList() {
  const router = useRouter();

  const [cars, setCars] = useState([]);
  const [carFilter, setCarFilter] = useState("");
  const [periodFilter, setPeriodFilter] = useState("week");
  const [expenses, setExpenses] = useState([]);
  const [error, setError] = useState("");
  // Gates the list section below -- without it, switching filters would
  // leave the previous (now-mismatched) results on screen until the new
  // request resolves, and the initial load could flash "no expenses" before
  // the first response arrives.
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    const carScope = carFilter ? `car=${carFilter}&` : "";
    let cancelled = false;
    setLoading(true);
    setError("");
    api(`/expenses/?${carScope}period=${periodFilter}`)
      .then((data) => { if (!cancelled) setExpenses(data.results || data); })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [carFilter, periodFilter]);

  useEffect(() => {
    api("/cars/").then((data) => setCars(data.results || data)).catch(() => {});
  }, []);

  useEffect(() => load(), [load]);

  return (
    <main className="px-4 pb-24 pt-6">
      <button onClick={() => router.push("/expenses")} className="mb-4 text-sm text-gray-500 dark:text-gray-400">‹ Back</button>
      <h1 className="mb-4 text-2xl font-bold">Expense log</h1>

      {error && <p className="mb-4 rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p>}

      <select className="input mb-4" value={carFilter} onChange={(e) => setCarFilter(e.target.value)}>
        <option value="">All cars</option>
        {cars.map((car) => (
          <option key={car.id} value={car.id}>{car.make} {car.model} {car.registration_number ? `— ${car.registration_number}` : ""}</option>
        ))}
      </select>

      <div className="mb-4">
        <FilterChips options={PERIODS} value={periodFilter} onChange={setPeriodFilter} />
      </div>

      {loading ? (
        <div className="flex justify-center py-6"><Spinner /></div>
      ) : (
        // Fixed-height + its own scroll container instead of letting the
        // list push the rest of the page down as more expenses get logged
        // (#25).
        <div className="max-h-[70vh] space-y-3 overflow-y-auto pb-1">
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
      )}

      <BottomNav />
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <ExpenseList />
    </AuthGuard>
  );
}
