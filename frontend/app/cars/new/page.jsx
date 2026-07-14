"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";

const FUEL_TYPES = ["petrol", "diesel", "hybrid", "electric"];

function NewCar() {
  const router = useRouter();
  const [form, setForm] = useState({
    make: "", model: "", year: "", registration_number: "", vin: "",
    color: "", fuel_type: "petrol", current_odometer_km: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const body = {
        ...form,
        year: form.year ? Number(form.year) : null,
        current_odometer_km: form.current_odometer_km ? Number(form.current_odometer_km) : 0,
      };
      const car = await api("/cars/", { method: "POST", body });
      router.replace(`/cars/${car.id}`);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  return (
    <main className="px-4 pb-10 pt-6">
      <button onClick={() => router.back()} className="mb-4 text-sm text-gray-500">‹ Back</button>
      <h1 className="mb-6 text-2xl font-bold">Add a Car</h1>

      {error && <p className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Make *</label>
            <input className="input" required value={form.make} onChange={update("make")} placeholder="Toyota" />
          </div>
          <div>
            <label className="label">Model *</label>
            <input className="input" required value={form.model} onChange={update("model")} placeholder="Corolla" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Year</label>
            <input className="input" type="number" min="1950" max="2100" value={form.year} onChange={update("year")} />
          </div>
          <div>
            <label className="label">Plate No.</label>
            <input className="input" value={form.registration_number} onChange={update("registration_number")} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Colour</label>
            <input className="input" value={form.color} onChange={update("color")} />
          </div>
          <div>
            <label className="label">Fuel</label>
            <select className="input" value={form.fuel_type} onChange={update("fuel_type")}>
              {FUEL_TYPES.map((fuel) => (
                <option key={fuel} value={fuel}>{fuel[0].toUpperCase() + fuel.slice(1)}</option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label className="label">Current odometer (km)</label>
          <input className="input" type="number" min="0" value={form.current_odometer_km} onChange={update("current_odometer_km")} />
        </div>
        <div>
          <label className="label">VIN</label>
          <input className="input" value={form.vin} onChange={update("vin")} />
        </div>

        <button className="btn-primary" disabled={loading}>{loading ? "Saving…" : "Add car"}</button>
      </form>
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <NewCar />
    </AuthGuard>
  );
}
