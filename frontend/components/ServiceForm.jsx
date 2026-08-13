"use client";

import { useState } from "react";
import { api } from "@/lib/api";

const SERVICE_TYPES = [
  ["minor_service", "Minor Service"],
  ["major_service", "Major Service"],
  ["oil_change", "Oil Change"],
  ["brakes", "Brakes"],
  ["tyres", "Tyres"],
  ["battery", "Battery"],
  ["other", "Other"],
];

// `record` (see #109) puts this in edit mode (PATCH) instead of create
// (POST) -- `carId` is only needed for create, since PATCH targets the
// record's own id and the backend doesn't accept reassigning `car`.
// `onCancel` (see #142) is optional -- the inline create flow on the car
// detail page has no other way out of this form (it's a toggled panel, not
// a page), so it needs one; the standalone edit page already has its own
// page-level "‹ Back" and passes the same handler through here too, for a
// closer-to-hand escape without scrolling back up.
export default function ServiceForm({ carId, record = null, onSaved, onCancel }) {
  const isEdit = !!record;
  const [form, setForm] = useState({
    service_type: record?.service_type || "minor_service",
    service_date: record?.service_date || "",
    odometer_km: record?.odometer_km ?? "",
    garage_name: record?.garage_name || "",
    cost: record?.cost ?? "",
    // Unlike create, don't default a missing interval to 5000km/6mo here --
    // a record with no interval (e.g. imported historical service history,
    // see #103) should stay interval-less on save unless the owner
    // deliberately sets one, not silently gain one just from being edited.
    interval_km: record ? (record.interval_km ?? "") : "5000",
    interval_months: record ? (record.interval_months ?? "") : "6",
    description: record?.description || "",
  });
  const [error, setError] = useState("");
  // See #143's review -- without this, Save then Cancel while the write is
  // still in flight could close the form (and fire onCancel's navigation)
  // before the record actually saved, or race onSaved with it.
  const [saving, setSaving] = useState(false);
  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      const fields = {
        service_type: form.service_type,
        service_date: form.service_date || undefined,
        odometer_km: Number(form.odometer_km),
        garage_name: form.garage_name,
        cost: form.cost || null,
        interval_km: form.interval_km ? Number(form.interval_km) : null,
        interval_months: form.interval_months ? Number(form.interval_months) : null,
        description: form.description,
      };

      if (isEdit) {
        await api(`/services/${record.id}/`, { method: "PATCH", body: fields });
      } else {
        await api("/services/", { method: "POST", body: { ...fields, car: carId } });
      }
      onSaved();
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="card space-y-3">
      <p className="font-semibold">{isEdit ? "Edit service" : "Log a service"}</p>
      {error && <p className="rounded-xl bg-red-50 dark:bg-red-500/10 p-2 text-sm text-red-700 dark:text-red-400">{error}</p>}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Type</label>
          <select className="input" value={form.service_type} onChange={update("service_type")}>
            {SERVICE_TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Date</label>
          <input className="input" type="date" value={form.service_date} onChange={update("service_date")} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Odometer (km) *</label>
          <input className="input" type="number" required min="0" value={form.odometer_km} onChange={update("odometer_km")} />
        </div>
        <div>
          <label className="label">Cost</label>
          <input className="input" type="number" step="0.01" min="0" value={form.cost} onChange={update("cost")} />
        </div>
      </div>
      <div>
        <label className="label">Garage</label>
        <input className="input" value={form.garage_name} onChange={update("garage_name")} />
      </div>
      <div className="rounded-xl bg-gray-50 dark:bg-gray-800/60 p-3">
        <p className="mb-2 text-[13px] font-medium text-gray-600 dark:text-gray-300">Next service — whichever comes first</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">After (km)</label>
            <input className="input" type="number" min="0" value={form.interval_km} onChange={update("interval_km")} placeholder="5000" />
          </div>
          <div>
            <label className="label">After (months)</label>
            <input className="input" type="number" min="0" value={form.interval_months} onChange={update("interval_months")} placeholder="6" />
          </div>
        </div>
      </div>
      <div>
        <label className="label">Notes</label>
        <textarea className="input" rows={2} value={form.description} onChange={update("description")} />
      </div>
      <button className="btn-primary" disabled={saving}>{isEdit ? "Save changes" : "Save service"}</button>
      {onCancel && (
        <button type="button" onClick={onCancel} className="btn-secondary" disabled={saving}>
          Cancel
        </button>
      )}
    </form>
  );
}
