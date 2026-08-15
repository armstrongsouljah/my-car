"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { trackSignal } from "@/lib/telemetry";
import AuthGuard from "@/components/AuthGuard";

const FUEL_TYPES = ["petrol", "diesel", "hybrid", "electric"];
const MAX_ROWS = 20;

function emptyRow() {
  return {
    id: crypto.randomUUID(),
    make: "", model: "", year: "", registration_number: "", fuel_type: "petrol", current_odometer_km: "",
  };
}

function isBlankRow(row) {
  return !row.make.trim() && !row.model.trim() && !row.registration_number.trim() && !row.year && !row.current_odometer_km;
}

function BulkAddCars() {
  const router = useRouter();
  const [rows, setRows] = useState([emptyRow(), emptyRow()]);
  const [rowErrors, setRowErrors] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [savedCount, setSavedCount] = useState(0);

  function updateRow(index, key, value) {
    setRows((prev) => prev.map((row, i) => (i === index ? { ...row, [key]: value } : row)));
  }

  function addRow() {
    setRows((prev) => (prev.length >= MAX_ROWS ? prev : [...prev, emptyRow()]));
  }

  function removeRow(index) {
    setRows((prev) => prev.filter((_, i) => i !== index));
    setRowErrors((prev) => {
      // Errors are keyed by row position, so removing a row shifts every
      // later row's error down by one — renumber instead of just deleting.
      const next = {};
      Object.entries(prev).forEach(([key, value]) => {
        const k = Number(key);
        if (k < index) next[k] = value;
        else if (k > index) next[k - 1] = value;
      });
      return next;
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    const candidates = rows
      .map((row, index) => ({ row, index }))
      .filter(({ row }) => !isBlankRow(row));

    if (candidates.length === 0) {
      setError("Fill in at least one car.");
      return;
    }

    const missingBrandModel = candidates.some(({ row }) => !row.make.trim() || !row.model.trim());
    if (missingBrandModel) {
      setError("Every car needs a make and model.");
      return;
    }

    setLoading(true);
    try {
      const cars = candidates.map(({ row }) => ({
        make: row.make.trim(),
        model: row.model.trim(),
        year: row.year ? Number(row.year) : null,
        registration_number: row.registration_number,
        fuel_type: row.fuel_type,
        current_odometer_km: row.current_odometer_km || 0,
      }));

      const data = await api("/cars/bulk/", { method: "POST", body: { cars } });
      const created = data?.created || [];
      const errors = data?.errors || [];

      if (created.length) {
        trackSignal("cars_bulk_added", { count: created.length });
        setSavedCount((prev) => prev + created.length);
      }

      if (errors.length === 0) {
        router.replace("/dashboard");
        return;
      }

      // Keep only the rows that failed so the owner can fix and resubmit;
      // successfully-created rows are already saved and drop out of the
      // form. Errors are keyed by the *original* row position, but rows is
      // about to be re-numbered by the filter below — remap error keys to
      // match the retained rows' new positions, not their old ones.
      const messagesByOriginalIndex = new Map(
        errors.map((e) => [candidates[e.index].index, Object.values(e.errors).flat().join(" ")])
      );
      const nextRows = [];
      const nextRowErrors = {};
      rows.forEach((row, i) => {
        if (messagesByOriginalIndex.has(i)) {
          nextRowErrors[nextRows.length] = messagesByOriginalIndex.get(i);
          nextRows.push(row);
        }
      });

      setRows(nextRows);
      setRowErrors(nextRowErrors);
      setError(`${created.length} car(s) added. Fix the row(s) below to add the rest.`);
    } catch (err) {
      const errors = err.data?.errors;
      if (Array.isArray(errors) && errors.length) {
        const nextRowErrors = {};
        errors.forEach((e) => {
          const originalIndex = candidates[e.index]?.index;
          if (originalIndex !== undefined) nextRowErrors[originalIndex] = Object.values(e.errors).flat().join(" ");
        });
        setRowErrors(nextRowErrors);
        setError("Some rows need fixing before they can be added.");
      } else {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="px-4 pb-10 pt-6">
      <button onClick={() => router.back()} className="mb-4 text-sm text-gray-500 dark:text-gray-400">‹ Back</button>
      <h1 className="mb-1 text-2xl font-bold">Add Multiple Cars</h1>
      <p className="mb-6 text-sm text-gray-500 dark:text-gray-400">
        Register several cars at once. Add photos and extra details later from each car&apos;s page.
      </p>

      {savedCount > 0 && (
        <p className="mb-4 rounded-xl bg-green-50 p-3 text-sm text-green-700 dark:bg-green-500/10 dark:text-green-400">
          {savedCount} car(s) saved so far.
        </p>
      )}
      {error && <p className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-400">{error}</p>}

      <form onSubmit={handleSubmit} className="space-y-3">
        {rows.map((row, index) => (
          <div key={row.id} className="card space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-gray-500 dark:text-gray-400">Car {index + 1}</p>
              {rows.length > 1 && (
                <button type="button" onClick={() => removeRow(index)} className="text-sm text-red-600 dark:text-red-400">
                  Remove
                </button>
              )}
            </div>
            {rowErrors[index] && <p className="text-[13px] text-red-600 dark:text-red-400">{rowErrors[index]}</p>}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Make *</label>
                <input className="input" placeholder="e.g. Toyota" value={row.make} onChange={(e) => updateRow(index, "make", e.target.value)} />
              </div>
              <div>
                <label className="label">Model *</label>
                <input className="input" placeholder="e.g. Corolla" value={row.model} onChange={(e) => updateRow(index, "model", e.target.value)} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Year</label>
                <input
                  className="input" type="number" placeholder="e.g. 2018"
                  value={row.year} onChange={(e) => updateRow(index, "year", e.target.value)}
                />
              </div>
              <div>
                <label className="label">Plate No. (optional)</label>
                <input className="input" value={row.registration_number} onChange={(e) => updateRow(index, "registration_number", e.target.value)} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Fuel</label>
                <select className="input" value={row.fuel_type} onChange={(e) => updateRow(index, "fuel_type", e.target.value)}>
                  {FUEL_TYPES.map((fuel) => (
                    <option key={fuel} value={fuel}>{fuel[0].toUpperCase() + fuel.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Odometer (km)</label>
                <input
                  className="input" type="number" min="0"
                  value={row.current_odometer_km} onChange={(e) => updateRow(index, "current_odometer_km", e.target.value)}
                />
              </div>
            </div>
          </div>
        ))}

        <button
          type="button" onClick={addRow} disabled={rows.length >= MAX_ROWS}
          className="btn-secondary w-full"
        >
          + Add another car
        </button>

        <button className="btn-primary w-full" disabled={loading}>
          {loading ? "Saving…" : "Add cars"}
        </button>
        <button type="button" onClick={() => router.back()} className="btn-secondary w-full" disabled={loading}>
          Cancel
        </button>
      </form>
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <BulkAddCars />
    </AuthGuard>
  );
}
