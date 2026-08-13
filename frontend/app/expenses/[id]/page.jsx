"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import ExpenseForm from "@/components/ExpenseForm";
import Spinner from "@/components/Spinner";

function EditExpense() {
  const { id } = useParams();
  const router = useRouter();
  const [expense, setExpense] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    // Reset before fetching, not just on id change — navigating directly
    // between two /expenses/[id] URLs (e.g. the browser's own back/forward,
    // not our in-app "‹ Back") reuses this same mounted route rather than
    // remounting it, so without this the previous expense's data (and the
    // ExpenseForm state keyed to it below) would hang around mid-fetch.
    setExpense(null);
    setError("");
    api(`/expenses/${id}/`).then(setExpense).catch((err) => setError(err.message));
  }, [id]);

  return (
    <main className="px-4 pb-24 pt-6">
      {/* Reached from the expense log list (#120), not the analytics page --
          back/save both return there rather than to /expenses. */}
      <button onClick={() => router.push("/expenses/list")} className="mb-4 text-sm text-gray-500 dark:text-gray-400">‹ Back</button>
      <h1 className="mb-6 text-2xl font-bold">Edit expense</h1>
      {error && <p className="rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p>}
      {!expense && !error && <div className="flex justify-center py-6"><Spinner /></div>}
      {/* Edit mode never renders/uses the car picker, so no need to fetch cars here. */}
      {expense && (
        <ExpenseForm
          key={id}
          cars={[]}
          expense={expense}
          onSaved={() => router.replace("/expenses/list")}
          onCancel={() => router.push("/expenses/list")}
        />
      )}
      <BottomNav />
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <EditExpense />
    </AuthGuard>
  );
}
