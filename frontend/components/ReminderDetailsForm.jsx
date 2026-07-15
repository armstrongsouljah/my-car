"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import TrackingMethodPicker from "@/components/TrackingMethodPicker";

const needsKm = (method) => method === "mileage" || method === "date_and_mileage";
const needsMonths = (method) => method === "date" || method === "date_and_mileage";

function todayLocal() {
  const now = new Date();
  const offsetMs = now.getTimezoneOffset() * 60 * 1000;
  return new Date(now.getTime() - offsetMs).toISOString().slice(0, 10);
}

export default function ReminderDetailsForm({ car, reminder = null, preset = null, trackingMethod, editableMethod = false, onSaved }) {
  const isEdit = !!reminder;
  const isCustom = isEdit ? !reminder.catalog_key : !preset;

  const [form, setForm] = useState({
    title: reminder?.title ?? preset?.title ?? "",
    tracking_method: reminder?.tracking_method ?? trackingMethod,
    interval_km: String(reminder?.interval_km ?? preset?.default_interval_km ?? ""),
    interval_months: String(reminder?.interval_months ?? preset?.default_interval_months ?? ""),
    baseline_odometer_km: String(reminder?.baseline_odometer_km ?? car.current_odometer_km ?? ""),
    baseline_date: reminder?.baseline_date ?? todayLocal(),
    notes: reminder?.notes ?? "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  const method = form.tracking_method;

  async function submit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const body = {
        title: form.title,
        tracking_method: method,
        interval_km: needsKm(method) ? Number(form.interval_km) : null,
        interval_months: needsMonths(method) ? Number(form.interval_months) : null,
        baseline_odometer_km: needsKm(method) ? Number(form.baseline_odometer_km) : null,
        baseline_date: needsMonths(method) ? form.baseline_date : null,
        notes: form.notes,
      };

      let saved;
      if (isEdit) {
        saved = await api(`/reminders/${reminder.id}/`, { method: "PATCH", body });
      } else {
        saved = await api("/reminders/", {
          method: "POST",
          body: {
            ...body,
            car: car.id,
            catalog_key: preset?.key || "",
            category: preset?.category || "other",
            is_essential: preset?.is_essential || false,
          },
        });
      }
      onSaved(saved);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      {error && <p className="rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p>}

      {isCustom && (
        <div>
          <label className="label">Reminder title *</label>
          <input className="input" required value={form.title} onChange={update("title")} />
        </div>
      )}

      {editableMethod && (
        <div>
          <p className="label">How should we remind you?</p>
          <TrackingMethodPicker value={method} onChange={(value) => setForm({ ...form, tracking_method: value })} />
        </div>
      )}

      {needsKm(method) && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Every (km) *</label>
            <input className="input" type="number" min="1" required value={form.interval_km} onChange={update("interval_km")} />
          </div>
          <div>
            <label className="label">Starting odometer (km) *</label>
            <input className="input" type="number" min="0" required value={form.baseline_odometer_km} onChange={update("baseline_odometer_km")} />
          </div>
        </div>
      )}

      {needsMonths(method) && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Every (months) *</label>
            <input className="input" type="number" min="1" required value={form.interval_months} onChange={update("interval_months")} />
          </div>
          <div>
            <label className="label">Starting date *</label>
            <input className="input" type="date" required value={form.baseline_date} onChange={update("baseline_date")} />
          </div>
        </div>
      )}

      <div>
        <label className="label">Notes</label>
        <textarea className="input" rows={2} value={form.notes} onChange={update("notes")} />
      </div>

      <button className="btn-primary" disabled={loading}>{loading ? "Saving…" : "Save reminder"}</button>
    </form>
  );
}
