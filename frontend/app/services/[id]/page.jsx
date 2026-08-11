"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import ConfirmDialog from "@/components/ConfirmDialog";
import ServiceForm from "@/components/ServiceForm";
import Spinner from "@/components/Spinner";

function EditService() {
  const { id } = useParams();
  const router = useRouter();
  const [record, setRecord] = useState(null);
  const [error, setError] = useState("");
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  useEffect(() => {
    // Reset before fetching, not just on id change -- see the same pattern
    // in app/expenses/[id]/page.jsx.
    setRecord(null);
    setError("");
    api(`/services/${id}/`).then(setRecord).catch((err) => setError(err.message));
  }, [id]);

  function backToCar() {
    router.push(record ? `/cars/${record.car}` : "/dashboard");
  }

  async function remove() {
    setRemoving(true);
    setDeleteError("");
    try {
      await api(`/services/${id}/`, { method: "DELETE" });
      router.replace(`/cars/${record.car}`);
    } catch (err) {
      setDeleteError(err.message);
      setRemoving(false);
    }
  }

  return (
    <main className="px-4 pb-24 pt-6">
      <button onClick={backToCar} className="mb-4 text-sm text-gray-500 dark:text-gray-400">‹ Back</button>
      <h1 className="mb-6 text-2xl font-bold">Edit service</h1>
      {error && <p className="rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p>}
      {!record && !error && <div className="flex justify-center py-6"><Spinner /></div>}
      {record && (
        <>
          <ServiceForm key={id} record={record} onSaved={() => router.replace(`/cars/${record.car}`)} />
          {deleteError && <p className="mt-4 rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{deleteError}</p>}
          <button
            onClick={() => setConfirmRemove(true)}
            className="mt-4 w-full rounded-xl border border-red-200 dark:border-red-500/30 bg-red-50 dark:bg-red-500/10 px-4 py-3 text-[15px] font-semibold text-red-600 dark:text-red-400"
          >
            Delete this service record
          </button>
        </>
      )}

      <ConfirmDialog
        open={confirmRemove}
        destructive
        loading={removing}
        title="Delete this service record?"
        message="This can't be undone. If it had a cost, its linked expense will be removed too."
        confirmLabel="Delete"
        cancelLabel="Keep record"
        onConfirm={remove}
        onCancel={() => setConfirmRemove(false)}
      />

      <BottomNav />
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <EditService />
    </AuthGuard>
  );
}
