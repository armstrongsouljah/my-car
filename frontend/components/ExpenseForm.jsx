"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { trackSignal } from "@/lib/telemetry";
import { CATEGORIES } from "@/lib/expenseCategories";

export default function ExpenseForm({ cars, expense = null, onSaved }) {
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
      <button className="btn-primary">{isEdit ? "Save changes" : "Save expense"}</button>
    </form>
  );
}
