"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { formatAmount } from "@/lib/currency";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";

function monthLabel(iso) {
  return new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

function periodSlug(iso) {
  return iso.slice(0, 7); // "2026-05-01" -> "2026-05"
}

function Reports() {
  const [months, setMonths] = useState(null);
  const [currency, setCurrency] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api("/expenses/analytics/?months=24")
      .then((data) => {
        setMonths([...(data.months || [])].reverse());
        setCurrency(data.currency);
      })
      .catch((err) => setError(err.message));
  }, []);

  return (
    <main className="px-4 pb-24 pt-6">
      <h1 className="mb-4 text-2xl font-bold">Expense reports</h1>

      {error && <p className="mb-4 rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p>}

      <Link
        href="/expenses/reports/all-time"
        className="card mb-4 flex items-center justify-between border-brand/30 bg-brand/5 text-sm active:scale-[0.99] dark:bg-brand/10"
      >
        <div>
          <p className="font-semibold">All-time report</p>
          <p className="text-[12px] text-gray-500 dark:text-gray-400">Every expense ever logged, across every car</p>
        </div>
        <span className="text-gray-300 dark:text-gray-600">›</span>
      </Link>

      <div className="space-y-3">
        {months?.map((month) => (
          <Link
            key={month.month}
            href={`/expenses/reports/${periodSlug(month.month)}`}
            className="card flex items-center justify-between text-sm active:scale-[0.99]"
          >
            <p className="font-semibold">{monthLabel(month.month)}</p>
            <div className="flex items-center gap-2">
              <p className="font-bold">{formatAmount(month.total, currency)}</p>
              <span className="text-gray-300 dark:text-gray-600">›</span>
            </div>
          </Link>
        ))}
        {months?.length === 0 && (
          <p className="text-center text-sm text-gray-400 dark:text-gray-500">No expenses logged yet.</p>
        )}
      </div>

      <BottomNav />
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <Reports />
    </AuthGuard>
  );
}
