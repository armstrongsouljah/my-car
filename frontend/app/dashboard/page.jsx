"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, getUser } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";

function Dashboard() {
  const [cars, setCars] = useState(null);
  const [error, setError] = useState("");
  const user = getUser();

  useEffect(() => {
    api("/cars/")
      .then((data) => setCars(data.results || data))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <main className="px-4 pb-24 pt-6">
      <header className="mb-6">
        <p className="text-sm text-gray-500">Welcome back{user?.first_name ? `, ${user.first_name}` : ""} 👋</p>
        <h1 className="text-2xl font-bold">Your Garage</h1>
      </header>

      {error && <p className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {cars === null && !error && <p className="text-sm text-gray-400">Loading…</p>}

      {cars?.length === 0 && (
        <div className="card text-center">
          <div className="text-3xl">🅿️</div>
          <p className="mt-2 font-semibold">No cars yet</p>
          <p className="mt-1 text-sm text-gray-500">Add your first car to start tracking services and expenses.</p>
        </div>
      )}

      <div className="space-y-3">
        {cars?.map((car) => (
          <Link key={car.id} href={`/cars/${car.id}`} className="card block active:scale-[0.99]">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold">
                  {car.make} {car.model} {car.year ? `(${car.year})` : ""}
                </p>
                <p className="mt-0.5 text-sm text-gray-500">
                  {car.registration_number || "No plate"} · {Number(car.current_odometer_km).toLocaleString()} km
                </p>
              </div>
              <span className="text-gray-300">›</span>
            </div>
          </Link>
        ))}
      </div>

      <Link
        href="/cars/new"
        className="fixed bottom-20 right-4 z-30 flex h-14 w-14 items-center justify-center rounded-full bg-gray-900 text-2xl text-white shadow-lg"
      >
        +
      </Link>

      <BottomNav />
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <Dashboard />
    </AuthGuard>
  );
}
