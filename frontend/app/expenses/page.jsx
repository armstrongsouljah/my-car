"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
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

function ExpenseForm({ cars, onSaved }) {
  const [form, setForm] = useState({
    car: cars[0]?.id || "", category: "fuel", amount: "", expense_date: "",
    vendor: "", description: "", odometer_km: "", litres: "",
  });
  const [error, setError] = useState("");
  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      await api("/expenses/", {
        method: "POST",
        body: {
          car: form.car,
          category: form.category,
          amount: form.amount,
          expense_date: form.expense_date || undefined,
          vendor: form.vendor,
          description: form.description,
          odometer_km: form.odometer_km ? Number(form.odometer_km) : null,
          litres: form.category === "fuel" && form.litres ? form.litres : null,
        },
      });
      onSaved();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={submit} className="card space-y-3">
      <p className="font-semibold">Log an expense</p>
      {error && <p className="rounded-xl bg-red-50 p-2 text-sm text-red-700">{error}</p>}
      <div>
        <label className="label">Car *</label>
        <select className="input" required value={form.car} onChange={update("car")}>
          {cars.map((car) => (
            <option key={car.id} value={car.id}>{car.make} {car.model} {car.registration_number ? `— ${car.registration_number}` : ""}</option>
          ))}
        </select>
      </div>
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
            <label className="label">Litres</label>
            <input className="input" type="number" step="0.01" min="0" value={form.litres} onChange={update("litres")} />
          </div>
          <div>
            <label className="label">Odometer (km)</label>
            <input className="input" type="number" min="0" value={form.odometer_km} onChange={update("odometer_km")} />
          </div>
        </div>
      )}
      <button className="btn-primary">Save expense</button>
    </form>
  );
}

function MonthChart({ months }) {
  if (!months?.length) return null;
  const max = Math.max(...months.map((m) => m.total), 1);

  return (
    <div className="card">
      <p className="mb-3 font-semibold">Month on month</p>
      <div className="flex items-end gap-2 overflow-x-auto pb-1" style={{ height: 140 }}>
        {months.map((month) => (
          <div key={month.month} className="flex min-w-[44px] flex-1 flex-col items-center justify-end gap-1">
            <p className="text-[10px] font-medium text-gray-500">{Math.round(month.total).toLocaleString()}</p>
            <div
              className="w-full rounded-t-md bg-gray-900"
              style={{ height: `${Math.max((month.total / max) * 100, 2)}%` }}
            />
            <p className="text-[10px] text-gray-400">{monthLabel(month.month)}</p>
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
  const [showForm, setShowForm] = useState(false);
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
      <h1 className="mb-4 text-2xl font-bold">Expenses</h1>

      {error && <p className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <select className="input mb-4" value={carFilter} onChange={(e) => setCarFilter(e.target.value)}>
        <option value="">All cars</option>
        {cars.map((car) => (
          <option key={car.id} value={car.id}>{car.make} {car.model} {car.registration_number ? `— ${car.registration_number}` : ""}</option>
        ))}
      </select>

      {latest && (
        <div className="mb-4 grid grid-cols-2 gap-3">
          <div className="card">
            <p className="text-[12px] text-gray-400">This month</p>
            <p className="text-xl font-bold">{latest.total.toLocaleString()}</p>
            {latest.change_percent_vs_previous_month !== null && latest.change_percent_vs_previous_month !== undefined && (
              <p className={`text-[12px] font-medium ${latest.change_percent_vs_previous_month > 0 ? "text-red-600" : "text-green-600"}`}>
                {latest.change_percent_vs_previous_month > 0 ? "▲" : "▼"} {Math.abs(latest.change_percent_vs_previous_month)}% vs last month
              </p>
            )}
          </div>
          <div className="card">
            <p className="text-[12px] text-gray-400">Last 12 months</p>
            <p className="text-xl font-bold">{analytics.grand_total.toLocaleString()}</p>
          </div>
        </div>
      )}

      <div className="mb-4">
        <MonthChart months={analytics?.months} />
      </div>

      {showForm ? (
        <ExpenseForm cars={cars} onSaved={() => { setShowForm(false); load(); }} />
      ) : (
        <button className="btn-secondary mb-4" onClick={() => setShowForm(true)} disabled={cars.length === 0}>
          + Log an expense
        </button>
      )}

      <div className="mt-4 space-y-3">
        {expenses.map((expense) => (
          <div key={expense.id} className="card flex items-center justify-between text-sm">
            <div>
              <p className="font-semibold">{CATEGORY_LABELS[expense.category] || expense.category}</p>
              <p className="text-gray-500">
                {expense.expense_date}
                {expense.vendor ? ` · ${expense.vendor}` : ""}
                {expense.litres ? ` · ${expense.litres} L` : ""}
              </p>
            </div>
            <p className="font-bold">{Number(expense.amount).toLocaleString()}</p>
          </div>
        ))}
        {expenses.length === 0 && <p className="text-center text-sm text-gray-400">No expenses logged yet.</p>}
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
