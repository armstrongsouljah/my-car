"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import ExpenseForm from "@/components/ExpenseForm";
import Spinner from "@/components/Spinner";

function NewExpense() {
  const router = useRouter();
  // null while loading, [] once loaded with no cars, otherwise the list.
  const [cars, setCars] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/cars/").then((data) => setCars(data.results || data)).catch((err) => setError(err.message));
  }, []);

  return (
    <main className="px-4 pb-24 pt-6">
      <button onClick={() => router.push("/expenses")} className="mb-4 text-sm text-gray-500 dark:text-gray-400">‹ Back</button>
      <h1 className="mb-6 text-2xl font-bold">Log an expense</h1>
      {error && <p className="rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p>}
      {!cars && !error && <div className="flex justify-center py-6"><Spinner /></div>}
      {cars && cars.length === 0 && (
        <Link href="/cars/new" className="card block text-center text-sm text-gray-500 dark:text-gray-400">
          Add a car first to log an expense against it.
        </Link>
      )}
      {cars && cars.length > 0 && (
        <ExpenseForm cars={cars} onSaved={() => router.replace("/expenses")} onCancel={() => router.push("/expenses")} />
      )}
      <BottomNav />
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <NewExpense />
    </AuthGuard>
  );
}
