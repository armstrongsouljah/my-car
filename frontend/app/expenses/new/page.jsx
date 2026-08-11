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

  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState("");
  const [scanResult, setScanResult] = useState(null);
  // Bumped on every successful scan so ExpenseForm below remounts and
  // re-seeds its (otherwise mount-once) internal state from the new
  // initialValues, instead of a second scan silently doing nothing.
  const [scanVersion, setScanVersion] = useState(0);

  useEffect(() => {
    api("/cars/").then((data) => setCars(data.results || data)).catch((err) => setError(err.message));
  }, []);

  // Extraction fields aren't car-specific -- any of the owner's own cars
  // satisfies the endpoint's ownership check, so this doesn't need to wait
  // on a car being chosen in the form below.
  async function scanReceipt(event) {
    const file = event.target.files?.[0];
    event.target.value = ""; // lets the same file be re-picked later
    if (!file || !cars?.length) return;
    setScanError("");
    setScanning(true);
    try {
      const body = new FormData();
      body.append("car", cars[0].id);
      body.append("image", file);
      const data = await api("/expenses/scan/", { method: "POST", body, isForm: true });
      setScanResult(data);
      setScanVersion((v) => v + 1);
    } catch (err) {
      setScanError(err.message);
    } finally {
      setScanning(false);
    }
  }

  const scanFoundNothing = scanResult && Object.values(scanResult).every((value) => value === null || value === "");

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
        <>
          <label className="card mb-4 flex cursor-pointer items-center justify-between text-sm font-medium active:scale-[0.99]">
            <span>{scanning ? "Reading receipt…" : "📷 Scan a receipt to prefill this"}</span>
            {scanning && <Spinner className="h-4 w-4" />}
            <input
              type="file"
              accept="image/*,.pdf"
              className="hidden"
              disabled={scanning}
              onChange={scanReceipt}
            />
          </label>
          {scanError && <p className="mb-4 rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{scanError}</p>}
          {scanFoundNothing && (
            <p className="mb-4 text-[13px] text-gray-400 dark:text-gray-500">
              Couldn&apos;t read much from that — go ahead and fill in the details below.
            </p>
          )}
          <ExpenseForm key={scanVersion} cars={cars} initialValues={scanResult} onSaved={() => router.replace("/expenses")} />
        </>
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
