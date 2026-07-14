"use client";

import { useRouter } from "next/navigation";
import AuthGuard from "@/components/AuthGuard";
import CarForm from "@/components/CarForm";

function NewCar() {
  const router = useRouter();

  return (
    <main className="px-4 pb-10 pt-6">
      <button onClick={() => router.back()} className="mb-4 text-sm text-gray-500">‹ Back</button>
      <h1 className="mb-6 text-2xl font-bold">Add a Car</h1>
      <CarForm onSaved={(car) => router.replace(`/cars/${car.id}`)} />
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
