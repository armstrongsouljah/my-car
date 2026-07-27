"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api, mediaUrl } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import ConfirmDialog from "@/components/ConfirmDialog";
import Spinner from "@/components/Spinner";
import StatusChip from "@/components/StatusChip";

const SERVICE_TYPES = [
  ["minor_service", "Minor Service"],
  ["major_service", "Major Service"],
  ["oil_change", "Oil Change"],
  ["brakes", "Brakes"],
  ["tyres", "Tyres"],
  ["battery", "Battery"],
  ["other", "Other"],
];

const INSPECTION_STATUSES = [
  ["passed", "Passed"],
  ["advisories", "Passed with Advisories"],
  ["failed", "Failed"],
];

function mask(value) {
  return "•".repeat(Math.max(value.length, 4));
}

function RevealableValue({ value, revealed, onToggle, className = "" }) {
  return (
    <span className={`inline-flex flex-wrap items-center gap-1.5 ${className}`}>
      <span className="break-all">{revealed ? value : mask(value)}</span>
      <button
        type="button"
        onClick={onToggle}
        className="text-[12px] font-medium text-gray-500 underline underline-offset-2 dark:text-gray-400"
      >
        {revealed ? "Hide" : "View"}
      </button>
    </span>
  );
}

function ServiceForm({ carId, onSaved }) {
  const [form, setForm] = useState({
    service_type: "minor_service", service_date: "", odometer_km: "",
    garage_name: "", cost: "", interval_km: "5000", interval_months: "6", description: "",
  });
  const [error, setError] = useState("");
  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      await api("/services/", {
        method: "POST",
        body: {
          car: carId,
          service_type: form.service_type,
          service_date: form.service_date || undefined,
          odometer_km: Number(form.odometer_km),
          garage_name: form.garage_name,
          cost: form.cost || null,
          interval_km: form.interval_km ? Number(form.interval_km) : null,
          interval_months: form.interval_months ? Number(form.interval_months) : null,
          description: form.description,
        },
      });
      onSaved();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={submit} className="card space-y-3">
      <p className="font-semibold">Log a service</p>
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
      <button className="btn-primary">Save service</button>
    </form>
  );
}

function InspectionForm({ carId, onSaved }) {
  const [form, setForm] = useState({
    inspection_date: "", odometer_km: "", status: "passed",
    inspector_name: "", notes: "", next_inspection_date: "",
  });
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const body = new FormData();
      body.append("car", carId);
      if (form.inspection_date) body.append("inspection_date", form.inspection_date);
      if (form.odometer_km) body.append("odometer_km", form.odometer_km);
      body.append("status", form.status);
      body.append("inspector_name", form.inspector_name);
      body.append("notes", form.notes);
      if (form.next_inspection_date) body.append("next_inspection_date", form.next_inspection_date);
      if (file) body.append("report", file);

      await api("/inspections/", { method: "POST", body, isForm: true });
      onSaved();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={submit} className="card space-y-3">
      <p className="font-semibold">Log an inspection</p>
      {error && <p className="rounded-xl bg-red-50 dark:bg-red-500/10 p-2 text-sm text-red-700 dark:text-red-400">{error}</p>}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Date</label>
          <input className="input" type="date" value={form.inspection_date} onChange={update("inspection_date")} />
        </div>
        <div>
          <label className="label">Result</label>
          <select className="input" value={form.status} onChange={update("status")}>
            {INSPECTION_STATUSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Odometer (km)</label>
          <input className="input" type="number" min="0" value={form.odometer_km} onChange={update("odometer_km")} />
        </div>
        <div>
          <label className="label">Next inspection</label>
          <input className="input" type="date" value={form.next_inspection_date} onChange={update("next_inspection_date")} />
        </div>
      </div>
      <div>
        <label className="label">Inspector / garage</label>
        <input className="input" value={form.inspector_name} onChange={update("inspector_name")} />
      </div>
      <div>
        <label className="label">Inspection report (optional)</label>
        <input className="input" type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={(e) => setFile(e.target.files?.[0] || null)} />
      </div>
      <div>
        <label className="label">Notes</label>
        <textarea className="input" rows={2} value={form.notes} onChange={update("notes")} />
      </div>
      <button className="btn-primary">Save inspection</button>
    </form>
  );
}

function CarDetail() {
  const { id } = useParams();
  const router = useRouter();
  const [car, setCar] = useState(null);
  const [servicesData, setServicesData] = useState([]);
  const [inspections, setInspections] = useState([]);
  const [tab, setTab] = useState("overview"); // overview | service | inspections
  const [showForm, setShowForm] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [showPlate, setShowPlate] = useState(false);
  const [showVin, setShowVin] = useState(false);

  const load = useCallback(() => {
    api(`/cars/${id}/`).then(setCar).catch((err) => setError(err.message));
    api(`/services/?car=${id}`).then((data) => setServicesData(data.results || data)).catch(() => {});
    api(`/inspections/?car=${id}`).then((data) => setInspections(data.results || data)).catch(() => {});
  }, [id]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    // This component instance is reused across /cars/[id] navigations (e.g.
    // one car's detail page linking to another's) — reset both reveal
    // toggles per car so the next car never opens with a previous car's
    // plate or VIN already shown.
    setShowPlate(false);
    setShowVin(false);
  }, [id]);

  async function deleteCar() {
    setRemoving(true);
    setDeleteError("");
    try {
      await api(`/cars/${id}/`, { method: "DELETE" });
      router.replace("/dashboard");
    } catch (err) {
      setDeleteError(err.message);
      setRemoving(false);
    }
  }

  if (error) return <main className="p-6"><p className="rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p></main>;
  if (!car) return <main className="flex justify-center p-10"><Spinner /></main>;

  return (
    <main className="px-4 pb-24 pt-6">
      <button onClick={() => router.push("/dashboard")} className="mb-4 text-sm text-gray-500 dark:text-gray-400">‹ Garage</button>

      {car.photo_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={mediaUrl(car.photo_url)} alt={`${car.make} ${car.model}`} className="mb-4 h-48 w-full rounded-2xl border border-gray-200 dark:border-gray-800 object-cover" />
      )}

      <header className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{car.make} {car.model} {car.year ? `(${car.year})` : ""}</h1>
          <p className="mt-1 flex flex-wrap items-center gap-1 text-sm text-gray-500 dark:text-gray-400">
            {car.registration_number ? (
              <RevealableValue value={car.registration_number} revealed={showPlate} onToggle={() => setShowPlate((v) => !v)} />
            ) : (
              "No plate"
            )}
            <span>· {Number(car.current_odometer_km).toLocaleString()} km</span>
          </p>
        </div>
        <Link href={`/cars/${id}/edit`} className="rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2 text-sm font-semibold">
          Edit
        </Link>
      </header>

      <div className="mb-4 space-y-2">
        {car.reminders?.map((reminder) => (
          <div key={reminder.kind} className="card flex items-center justify-between gap-3 py-3">
            <div>
              <p className="text-[13px] font-semibold capitalize">{reminder.kind}</p>
              <p className="text-[13px] text-gray-500 dark:text-gray-400">{reminder.message}</p>
            </div>
            <StatusChip status={reminder.status} />
          </div>
        ))}
      </div>

      <div className="mb-4 grid grid-cols-3 rounded-xl bg-gray-200 dark:bg-gray-800 p-1 text-[13px] font-semibold">
        {["overview", "service", "inspections"].map((key) => (
          <button
            key={key}
            className={`rounded-lg py-2 capitalize ${tab === key ? "bg-white shadow dark:bg-gray-700 dark:text-white" : "text-gray-500 dark:text-gray-400"}`}
            onClick={() => { setTab(key); setShowForm(false); }}
          >
            {key}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="space-y-3">
          <div className="card grid grid-cols-2 gap-y-3 text-sm">
            <div><p className="text-gray-400 dark:text-gray-500">Colour</p><p className="font-medium">{car.color || "—"}</p></div>
            <div><p className="text-gray-400 dark:text-gray-500">Fuel</p><p className="font-medium capitalize">{car.fuel_type}</p></div>
            <div>
              <p className="text-gray-400 dark:text-gray-500">VIN</p>
              {car.vin ? (
                <p className="font-medium">
                  <RevealableValue value={car.vin} revealed={showVin} onToggle={() => setShowVin((v) => !v)} />
                </p>
              ) : (
                <p className="font-medium">—</p>
              )}
            </div>
            <div><p className="text-gray-400 dark:text-gray-500">Odometer</p><p className="font-medium">{Number(car.current_odometer_km).toLocaleString()} km</p></div>
          </div>
          {car.notes && <div className="card text-sm text-gray-600 dark:text-gray-300">{car.notes}</div>}
          {deleteError && <p className="rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{deleteError}</p>}
          <button onClick={() => setConfirmRemove(true)} className="w-full rounded-xl border border-red-200 dark:border-red-500/30 bg-red-50 dark:bg-red-500/10 px-4 py-3 text-[15px] font-semibold text-red-600 dark:text-red-400">
            Remove car
          </button>
        </div>
      )}

      <ConfirmDialog
        open={confirmRemove}
        destructive
        loading={removing}
        title="Remove this car?"
        message={`${car.make} ${car.model} and all its service history, inspections and expenses will be permanently removed. This can't be undone.`}
        confirmLabel="Remove car"
        cancelLabel="Keep car"
        onConfirm={deleteCar}
        onCancel={() => setConfirmRemove(false)}
      />

      {tab === "service" && (
        <div className="space-y-3">
          {showForm ? (
            <ServiceForm carId={id} onSaved={() => { setShowForm(false); load(); }} />
          ) : (
            <button className="btn-secondary" onClick={() => setShowForm(true)}>+ Log a service</button>
          )}
          {servicesData.length === 0 && !showForm && <p className="text-center text-sm text-gray-400 dark:text-gray-500">No services logged yet.</p>}
          {servicesData.map((record) => (
            <div key={record.id} className="card text-sm">
              <div className="flex items-center justify-between">
                <p className="font-semibold">{record.service_type_display}</p>
                <p className="text-gray-500 dark:text-gray-400">{record.service_date}</p>
              </div>
              <p className="mt-1 text-gray-500 dark:text-gray-400">
                {Number(record.odometer_km).toLocaleString()} km
                {record.garage_name ? ` · ${record.garage_name}` : ""}
                {record.cost ? ` · ${record.cost}` : ""}
              </p>
              {(record.next_due_odometer_km || record.next_due_date) && (
                <p className="mt-1 text-[13px] text-gray-400 dark:text-gray-500">
                  Next due:{" "}
                  {[
                    record.next_due_odometer_km ? `${Number(record.next_due_odometer_km).toLocaleString()} km` : null,
                    record.next_due_date,
                  ].filter(Boolean).join(" or ")}{" "}
                  — whichever comes first
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === "inspections" && (
        <div className="space-y-3">
          {showForm ? (
            <InspectionForm carId={id} onSaved={() => { setShowForm(false); load(); }} />
          ) : (
            <button className="btn-secondary" onClick={() => setShowForm(true)}>+ Log an inspection</button>
          )}
          {inspections.length === 0 && !showForm && <p className="text-center text-sm text-gray-400 dark:text-gray-500">No inspections logged yet.</p>}
          {inspections.map((inspection) => (
            <div key={inspection.id} className="card text-sm">
              <div className="flex items-center justify-between">
                <p className="font-semibold">{inspection.status_display}</p>
                <p className="text-gray-500 dark:text-gray-400">{inspection.inspection_date}</p>
              </div>
              {inspection.inspector_name && <p className="mt-1 text-gray-500 dark:text-gray-400">{inspection.inspector_name}</p>}
              {inspection.next_inspection_date && (
                <p className="mt-1 text-[13px] text-gray-400 dark:text-gray-500">Next inspection: {inspection.next_inspection_date}</p>
              )}
              {inspection.report_url && (
                <a href={inspection.report_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-[13px] font-medium underline">
                  View report
                </a>
              )}
            </div>
          ))}
        </div>
      )}

      <BottomNav />
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <CarDetail />
    </AuthGuard>
  );
}
