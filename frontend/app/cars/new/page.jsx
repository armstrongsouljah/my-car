"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import AuthGuard from "@/components/AuthGuard";
import CarForm from "@/components/CarForm";

function NewCar() {
  const router = useRouter();

  return (
    <main className="px-4 pb-10 pt-6">
      <button onClick={() => router.back()} className="mb-4 text-sm text-gray-500 dark:text-gray-400">‹ Back</button>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Add a Car</h1>
        <Link href="/cars/bulk" className="btn-chip">
          Add multiple →
        </Link>
      </div>
      <CarForm onSaved={(car) => router.replace(`/cars/${car.id}`)} onCancel={() => router.back()} />
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
