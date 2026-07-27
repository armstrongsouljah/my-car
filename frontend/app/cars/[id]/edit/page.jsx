"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import CarForm from "@/components/CarForm";
import Spinner from "@/components/Spinner";

function EditCar() {
  const { id } = useParams();
  const router = useRouter();
  const [car, setCar] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api(`/cars/${id}/`).then(setCar).catch((err) => setError(err.message));
  }, [id]);

  return (
    <main className="px-4 pb-10 pt-6">
      <button onClick={() => router.push(`/cars/${id}`)} className="mb-4 text-sm text-gray-500 dark:text-gray-400">‹ Back</button>
      <h1 className="mb-6 text-2xl font-bold">Edit Car</h1>
      {error && <p className="rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p>}
      {!car && !error && <div className="flex justify-center py-6"><Spinner /></div>}
      {car && <CarForm car={car} onSaved={() => router.replace(`/cars/${id}`)} />}
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <EditCar />
    </AuthGuard>
  );
}
