"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { formatAmount } from "@/lib/currency";
import { trackSignal } from "@/lib/telemetry";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";

const CATEGORIES = [
  ["garage_visit", "Garage Visit"],
  ["modification_parts", "Modification / Parts"],
  ["fuel", "Fuel"],
  ["insurance", "Insurance"],
  ["tax_licensing", "Tax & Licensing"],
  ["cleaning", "Cleaning & Detailing"],
  ["other", "Other"],
];

const CATEGORY_LABELS = Object.fromEntries(CATEGORIES);

// Fixed hue order (issue #58) — assigned by category identity, never
// reordered/cycled; see the CVD-validation comment above the CSS vars in
// globals.css. Literal "bg-chart-N" strings so Tailwind's JIT scanner can
// find them (a templated `bg-${var}` class name would not be generated).
const CATEGORY_COLOR_CLASS = {
  garage_visit: "bg-chart-1",
  modification_parts: "bg-chart-2",
  fuel: "bg-chart-3",
  insurance: "bg-chart-4",
  tax_licensing: "bg-chart-5",
  cleaning: "bg-chart-6",
  other: "bg-chart-7",
};

const BAR_AREA_HEIGHT = 100; // px — the bar's own max height inside MonthChart's 150px row

function monthLabel(iso) {
  return new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", year: "2-digit" });
}

function ExpenseForm({ cars, expense = null, onSaved, onCancel }) {
  const isEdit = !!expense;
  const initialCostPerLitre =
    expense?.category === "fuel" && expense.litres > 0 ? (Number(expense.amount) / Number(expense.litres)).toFixed(2) : "";

  const [form, setForm] = useState({
    car: expense?.car || cars[0]?.id || "",
    category: expense?.category || "fuel",
    amount: expense?.amount ?? "",
    expense_date: expense?.expense_date || "",
    vendor: expense?.vendor || "",
    description: expense?.description || "",
    odometer_km: expense?.odometer_km ?? "",
    cost_per_litre: initialCostPerLitre,
  });
  const [error, setError] = useState("");
  // Editing an existing fuel expense without touching amount/category/cost
  // per litre should leave the stored litres exactly as they were, rather
  // than round-tripping through the rounded cost-per-litre display value.
  const [fuelInputsChanged, setFuelInputsChanged] = useState(false);
  const update = (key) => (event) => {
    if (isEdit && (key === "amount" || key === "category" || key === "cost_per_litre")) setFuelInputsChanged(true);
    setForm({ ...form, [key]: event.target.value });
  };

  const litres =
    isEdit && !fuelInputsChanged && expense.category === "fuel" && expense.litres != null
      ? Number(expense.litres)
      : form.category === "fuel" && form.amount && form.cost_per_litre && Number(form.cost_per_litre) > 0
        ? Number(form.amount) / Number(form.cost_per_litre)
        : null;

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const fields = {
        category: form.category,
        amount: form.amount,
        expense_date: form.expense_date || undefined,
        vendor: form.vendor,
        description: form.description,
        odometer_km: form.odometer_km ? Number(form.odometer_km) : null,
        litres: litres !== null ? litres.toFixed(2) : null,
      };

      if (isEdit) {
        await api(`/expenses/${expense.id}/`, { method: "PATCH", body: fields });
        trackSignal("expense_updated", { category: form.category });
      } else {
        await api("/expenses/", { method: "POST", body: { ...fields, car: form.car } });
        trackSignal("expense_added", { category: form.category });
      }
      onSaved();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={submit} className="card space-y-3">
      <p className="font-semibold">{isEdit ? "Edit expense" : "Log an expense"}</p>
      {error && <p className="rounded-xl bg-red-50 dark:bg-red-500/10 p-2 text-sm text-red-700 dark:text-red-400">{error}</p>}
      {!isEdit && (
        <div>
          <label className="label">Car *</label>
          <select className="input" required value={form.car} onChange={update("car")}>
            {cars.map((car) => (
              <option key={car.id} value={car.id}>{car.make} {car.model} {car.registration_number ? `— ${car.registration_number}` : ""}</option>
            ))}
          </select>
        </div>
      )}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Category</label>
          <select className="input" value={form.category} onChange={update("category")}>
            {CATEGORIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Amount *</label>
          <input className="input" type="number" step="0.01" min="0" required value={form.amount} onChange={update("amount")} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Date</label>
          <input className="input" type="date" value={form.expense_date} onChange={update("expense_date")} />
        </div>
        <div>
          <label className="label">Vendor</label>
          <input className="input" value={form.vendor} onChange={update("vendor")} />
        </div>
      </div>
      {form.category === "fuel" && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Cost per litre</label>
            <input className="input" type="number" step="0.01" min="0" value={form.cost_per_litre} onChange={update("cost_per_litre")} />
            {litres !== null && (
              <p className="mt-1 text-[12px] text-gray-400 dark:text-gray-500">≈ {litres.toFixed(2)} L</p>
            )}
          </div>
          <div>
            <label className="label">Odometer (km)</label>
            <input className="input" type="number" min="0" value={form.odometer_km} onChange={update("odometer_km")} />
          </div>
        </div>
      )}
      <div>
        <label className="label">Notes</label>
        <textarea className="input" rows={2} placeholder="What was this for?" value={form.description} onChange={update("description")} />
      </div>
      <div className="flex gap-2">
        <button className="btn-primary">{isEdit ? "Save changes" : "Save expense"}</button>
        <button type="button" onClick={onCancel} className="btn-secondary">Cancel</button>
      </div>
    </form>
  );
}

function YearNav({ year, onPrevYear, onNextYear, canGoPrev, canGoNext }) {
  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={onPrevYear}
        disabled={!canGoPrev}
        aria-label="Previous year"
        className="flex h-6 w-6 items-center justify-center rounded-full text-gray-400 outline-none transition hover:bg-gray-100 disabled:opacity-30 disabled:hover:bg-transparent dark:text-gray-500 dark:hover:bg-gray-800"
      >
        ‹
      </button>
      <span className="w-10 text-center text-[13px] font-medium tabular-nums">{year}</span>
      <button
        type="button"
        onClick={onNextYear}
        disabled={!canGoNext}
        aria-label="Next year"
        className="flex h-6 w-6 items-center justify-center rounded-full text-gray-400 outline-none transition hover:bg-gray-100 disabled:opacity-30 disabled:hover:bg-transparent dark:text-gray-500 dark:hover:bg-gray-800"
      >
        ›
      </button>
    </div>
  );
}

function MonthChart({ months, currency, year, onPrevYear, onNextYear, canGoPrev, canGoNext }) {
  const [selectedKey, setSelectedKey] = useState(null);

  const hasData = !!months?.length;
  const max = hasData ? Math.max(...months.map((m) => m.total), 1) : 1;
  // Only legend/detail categories that actually appear somewhere in the
  // visible range — no point listing all 7 fixed categories if this car
  // has never had e.g. an insurance expense.
  const activeCategories = hasData ? CATEGORIES.filter(([key]) => months.some((m) => (m.by_category?.[key] || 0) > 0)) : [];
  const selectedMonth = hasData ? months.find((m) => m.month === selectedKey) || months[months.length - 1] : null;

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <p className="font-semibold">Month on month</p>
        <YearNav year={year} onPrevYear={onPrevYear} onNextYear={onNextYear} canGoPrev={canGoPrev} canGoNext={canGoNext} />
      </div>

      {!hasData && (
        <p className="py-10 text-center text-[13px] text-gray-400 dark:text-gray-500">No expenses logged in {year}.</p>
      )}

      {hasData && (
        <>
          {activeCategories.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-x-3 gap-y-1.5">
              {activeCategories.map(([key, label]) => (
                <span key={key} className="flex items-center gap-1.5 text-[11px] text-gray-500 dark:text-gray-400">
                  <span className={`h-2 w-2 rounded-full ${CATEGORY_COLOR_CLASS[key]}`} />
                  {label}
                </span>
              ))}
            </div>
          )}

          <div className="flex items-end gap-1 overflow-x-auto pb-1" style={{ height: 150 }}>
            {months.map((month) => {
              const isSelected = month.month === selectedMonth.month;
              const segments = CATEGORIES
                .map(([key]) => [key, month.by_category?.[key] || 0])
                .filter(([, value]) => value > 0);
              // Pixels, not a percentage: this div's immediate parent (the
              // button) has no defined height of its own (items-end, not
              // stretch), so a percentage height here would resolve against
              // "auto" and collapse to 0 — see #58.
              const barHeight = Math.max((month.total / max) * BAR_AREA_HEIGHT, 2);

              return (
                <button
                  type="button"
                  key={month.month}
                  onClick={() => setSelectedKey(month.month)}
                  onFocus={() => setSelectedKey(month.month)}
                  aria-label={`${monthLabel(month.month)}: ${formatAmount(month.total, currency)}`}
                  className={`flex min-w-[32px] flex-1 flex-col items-center justify-end gap-1 rounded-lg pt-2 outline-none transition ${
                    isSelected ? "bg-brand/10" : "hover:bg-gray-100 dark:hover:bg-gray-800/60"
                  }`}
                >
                  <p className="text-[10px] font-medium text-gray-500 dark:text-gray-400">
                    {formatAmount(Math.round(month.total), currency)}
                  </p>
                  <div
                    className="flex w-full max-w-[24px] flex-col justify-end gap-[2px] overflow-hidden rounded-t-[4px]"
                    style={{ height: barHeight }}
                  >
                    {segments.length === 0 ? (
                      <div className="w-full flex-1 bg-gray-200 dark:bg-gray-700" />
                    ) : (
                      segments.map(([key, value]) => (
                        <div
                          key={key}
                          className={`w-full ${CATEGORY_COLOR_CLASS[key]}`}
                          style={{ flexGrow: value, flexBasis: 0 }}
                        />
                      ))
                    )}
                  </div>
                  <p className="text-[10px] text-gray-400 dark:text-gray-500">{monthLabel(month.month)}</p>
                </button>
              );
            })}
          </div>

          <div className="mt-3 rounded-xl bg-gray-50 p-3 dark:bg-gray-800/60">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-[13px] font-semibold">{monthLabel(selectedMonth.month)}</p>
              <p className="text-[13px] font-bold">{formatAmount(selectedMonth.total, currency)}</p>
            </div>
            {selectedMonth.total === 0 ? (
              <p className="text-[12px] text-gray-400 dark:text-gray-500">No expenses logged.</p>
            ) : (
              <div className="space-y-1.5">
                {CATEGORIES.filter(([key]) => (selectedMonth.by_category?.[key] || 0) > 0).map(([key, label]) => (
                  <div key={key} className="flex items-center justify-between text-[12px]">
                    <span className="flex items-center gap-1.5 text-gray-600 dark:text-gray-300">
                      <span className={`h-2 w-2 rounded-full ${CATEGORY_COLOR_CLASS[key]}`} />
                      {label}
                    </span>
                    <span className="font-medium text-gray-900 dark:text-gray-100">
                      {formatAmount(selectedMonth.by_category[key], currency)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function Expenses() {
  const currentYear = new Date().getFullYear();

  const [cars, setCars] = useState([]);
  const [carFilter, setCarFilter] = useState("");
  const [yearFilter, setYearFilter] = useState(currentYear);
  // Clamps how far back "‹" can go on the chart — null (still loading, or
  // never resolved) means don't clamp yet rather than trap the user behind
  // a disabled button.
  const [joinYear, setJoinYear] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [formTarget, setFormTarget] = useState(null); // null | "new" | expense object
  const [error, setError] = useState("");

  const load = useCallback(() => {
    const carScope = carFilter ? `car=${carFilter}&` : "";
    // Explicit ?year= (see #58): a calendar year, not a rolling
    // trailing-12-months window that could span two different years.
    // yearFilter lets the owner browse past years (and, further back, an
    // all-time report — see the Reports page) rather than only ever seeing
    // the current one.
    api(`/expenses/analytics/?${carScope}year=${yearFilter}`).then(setAnalytics).catch((err) => setError(err.message));
    api(`/expenses/${carFilter ? `?car=${carFilter}` : ""}`).then((data) => setExpenses(data.results || data)).catch(() => {});
  }, [carFilter, yearFilter]);

  useEffect(() => {
    api("/cars/").then((data) => setCars(data.results || data)).catch(() => {});
    api("/auth/profile/")
      .then((data) => { if (data.date_joined) setJoinYear(new Date(data.date_joined).getFullYear()); })
      .catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

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
            <p className="text-[12px] text-gray-400 dark:text-gray-500">{isCurrentYear ? "Annual Total" : `${yearFilter} Total`}</p>
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
          canGoPrev={joinYear === null || yearFilter > joinYear}
          canGoNext={yearFilter < currentYear}
        />
      </div>

      {formTarget ? (
        <div className="mb-4">
          <ExpenseForm
            key={formTarget === "new" ? "new" : formTarget.id}
            cars={cars}
            expense={formTarget === "new" ? null : formTarget}
            onSaved={() => { setFormTarget(null); load(); }}
            onCancel={() => setFormTarget(null)}
          />
        </div>
      ) : (
        <button className="btn-secondary mb-4" onClick={() => setFormTarget("new")} disabled={cars.length === 0}>
          + Log an expense
        </button>
      )}

      <div className="mt-4 space-y-3">
        {expenses.map((expense) => (
          <button
            key={expense.id}
            onClick={() => setFormTarget(expense)}
            className="card flex w-full items-center justify-between text-left text-sm active:scale-[0.99]"
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
          </button>
        ))}
        {expenses.length === 0 && <p className="text-center text-sm text-gray-400 dark:text-gray-500">No expenses logged yet.</p>}
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
