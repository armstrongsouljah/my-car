"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import Spinner from "@/components/Spinner";

function carLabel(car) {
  return `${car.make} ${car.model}${car.year ? ` (${car.year})` : ""}`;
}

function CarMileageRow({ car, onSaved }) {
  const [value, setValue] = useState("");
  const [allowDecrease, setAllowDecrease] = useState(false);
  const [showOverride, setShowOverride] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const odometer = Number(value);
    if (!value || !Number.isFinite(odometer) || odometer < 0) {
      setError("Enter a valid mileage.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      const updated = await api(`/cars/${car.id}/`, {
        method: "PATCH",
        body: { current_odometer_km: odometer, allow_odometer_decrease: allowDecrease },
      });
      setSaved(true);
      setValue("");
      setShowOverride(false);
      setAllowDecrease(false);
      onSaved(updated);
    } catch (err) {
      setError(err.message);
      // The backwards-reading guard is the only 400 this endpoint raises for
      // this form — surface the override instead of a dead-end error.
      if (err.status === 400) setShowOverride(true);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card">
      <div className="flex items-center gap-3">
        {car.photo_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={car.photo_url} alt="" className="h-12 w-12 rounded-xl object-cover" />
        )}
        <div>
          <p className="font-semibold">{carLabel(car)}</p>
          <p className="text-[13px] text-gray-400 dark:text-gray-500">
            Current reading: {Number(car.current_odometer_km).toLocaleString()} km
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="mt-3 flex items-end gap-2">
        <div className="flex-1">
          <label className="label" htmlFor={`odo-${car.id}`}>New mileage (km)</label>
          <input
            id={`odo-${car.id}`}
            className="input"
            type="number"
            inputMode="numeric"
            min="0"
            placeholder={String(car.current_odometer_km)}
            value={value}
            onChange={(event) => {
              setValue(event.target.value);
              setSaved(false);
            }}
          />
        </div>
        <button className="btn-primary w-auto px-5" disabled={saving}>
          {saving ? "Saving…" : "Update"}
        </button>
      </form>

      {showOverride && (
        <label className="mt-2 flex items-start gap-2 text-[13px] text-gray-600 dark:text-gray-400">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={allowDecrease}
            onChange={(event) => setAllowDecrease(event.target.checked)}
          />
          I replaced the engine/odometer — this lower reading is correct
        </label>
      )}

      {error && <p className="mt-2 text-[13px] text-red-600 dark:text-red-400">{error}</p>}
      {saved && !error && <p className="mt-2 text-[13px] text-brand">Updated ✓</p>}
    </div>
  );
}

function MileageUpdate() {
  const [cars, setCars] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/cars/")
      .then((data) => setCars(data.results || data))
      .catch((err) => setError(err.message));
  }, []);

  function handleSaved(updatedCar) {
    setCars((prev) =>
      prev.map((car) => (car.id === updatedCar.id ? { ...car, current_odometer_km: updatedCar.current_odometer_km } : car))
    );
  }

  return (
    <main className="px-4 pb-24 pt-6">
      <Link href="/dashboard" className="mb-4 inline-block text-sm text-gray-500 dark:text-gray-400">
        ‹ Back
      </Link>
      <h1 className="mb-1 text-2xl font-bold">Update mileage</h1>
      <p className="mb-6 text-sm text-gray-500 dark:text-gray-400">
        Keep your odometer readings current so service reminders stay accurate.
      </p>

      {error && (
        <p className="mb-4 rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p>
      )}
      {cars === null && !error && (
        <div className="flex justify-center py-6">
          <Spinner />
        </div>
      )}
      {cars?.length === 0 && (
        <div className="card text-center text-sm text-gray-500 dark:text-gray-400">
          Add a car to start tracking mileage.
        </div>
      )}

      <div className="space-y-4">
        {cars?.map((car) => (
          <CarMileageRow key={car.id} car={car} onSaved={handleSaved} />
        ))}
      </div>

      <BottomNav />
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <MileageUpdate />
    </AuthGuard>
  );
}
