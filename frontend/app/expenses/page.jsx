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

function MonthChart({ months, currency }) {
  if (!months?.length) return null;
  const max = Math.max(...months.map((m) => m.total), 1);

  return (
    <div className="card">
      <p className="mb-3 font-semibold">Month on month</p>
      <div className="flex items-end gap-2 overflow-x-auto pb-1" style={{ height: 140 }}>
        {months.map((month) => (
          <div key={month.month} className="flex min-w-[44px] flex-1 flex-col items-center justify-end gap-1">
            <p className="text-[10px] font-medium text-gray-500 dark:text-gray-400">{formatAmount(Math.round(month.total), currency)}</p>
            <div
              className="w-full rounded-t-md bg-gray-900 dark:bg-white"
              style={{ height: `${Math.max((month.total / max) * 100, 2)}%` }}
            />
            <p className="text-[10px] text-gray-400 dark:text-gray-500">{monthLabel(month.month)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function Expenses() {
  const [cars, setCars] = useState([]);
  const [carFilter, setCarFilter] = useState("");
  const [analytics, setAnalytics] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [formTarget, setFormTarget] = useState(null); // null | "new" | expense object
  const [error, setError] = useState("");

  const load = useCallback(() => {
    const scope = carFilter ? `?car=${carFilter}` : "";
    api(`/expenses/analytics/${scope}`).then(setAnalytics).catch((err) => setError(err.message));
    api(`/expenses/${scope}`).then((data) => setExpenses(data.results || data)).catch(() => {});
  }, [carFilter]);

  useEffect(() => {
    api("/cars/").then((data) => setCars(data.results || data)).catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

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
            <p className="text-[12px] text-gray-400 dark:text-gray-500">This month</p>
            <p className="text-xl font-bold">{formatAmount(latest.total, analytics.currency)}</p>
            {latest.change_percent_vs_previous_month !== null && latest.change_percent_vs_previous_month !== undefined && (
              <p className={`text-[12px] font-medium ${latest.change_percent_vs_previous_month > 0 ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"}`}>
                {latest.change_percent_vs_previous_month > 0 ? "▲" : "▼"} {Math.abs(latest.change_percent_vs_previous_month)}% vs last month
              </p>
            )}
          </div>
          <div className="card">
            <p className="text-[12px] text-gray-400 dark:text-gray-500">Last 12 months</p>
            <p className="text-xl font-bold">{formatAmount(analytics.grand_total, analytics.currency)}</p>
          </div>
        </div>
      )}

      <div className="mb-4">
        <MonthChart months={analytics?.months} currency={analytics?.currency} />
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
