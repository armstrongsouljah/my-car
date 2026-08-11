"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import Spinner from "@/components/Spinner";

const SERVICE_TYPES = [
  ["minor_service", "Minor Service"],
  ["major_service", "Major Service"],
  ["oil_change", "Oil Change"],
  ["brakes", "Brakes"],
  ["tyres", "Tyres"],
  ["battery", "Battery"],
  ["other", "Other"],
];

// A locally-generated id so each proposed row can be tracked/edited/removed
// independently in the review step — server-issued ids don't exist yet
// since nothing's saved until confirm.
let nextRowId = 0;

function toRow(record) {
  return { ...record, rowId: nextRowId++, include: !record.possible_duplicate };
}

function ImportHistory() {
  const { id: carId } = useParams();
  const router = useRouter();

  const [file, setFile] = useState(null);
  const [extracting, setExtracting] = useState(false);
  const [rows, setRows] = useState(null); // null until extraction succeeds
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  function update(rowId, key) {
    return (event) => {
      const value = event.target.value;
      setRows((current) => current.map((row) => (row.rowId === rowId ? { ...row, [key]: value } : row)));
    };
  }

  function toggleInclude(rowId) {
    setRows((current) => current.map((row) => (row.rowId === rowId ? { ...row, include: !row.include } : row)));
  }

  async function extract(event) {
    event.preventDefault();
    setError("");
    setExtracting(true);
    try {
      const body = new FormData();
      body.append("car", carId);
      body.append("file", file);
      const data = await api("/history-import/extract/", { method: "POST", body, isForm: true });
      setRows(data.records.map(toRow));
    } catch (err) {
      setError(err.message);
    } finally {
      setExtracting(false);
    }
  }

  async function confirm() {
    setError("");
    setSaving(true);
    try {
      const records = rows
        .filter((row) => row.include)
        .map(({ kind, date, vendor, description, cost, service_type }) => ({
          kind, date, vendor, description,
          cost: cost === "" ? null : cost,
          service_type: kind === "service" ? service_type : null,
        }));
      const data = await api("/history-import/confirm/", { method: "POST", body: { car: carId, records } });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (result) {
    return (
      <main className="px-4 pb-24 pt-6">
        <h1 className="mb-4 text-2xl font-bold">Import complete</h1>
        <div className="card space-y-1 text-sm">
          <p>{result.service_records_created} service record(s) added</p>
          <p>{result.expenses_created} expense(s) added</p>
          {result.duplicates_skipped > 0 && (
            <p className="text-gray-400 dark:text-gray-500">{result.duplicates_skipped} skipped as likely already logged</p>
          )}
        </div>
        <button className="btn-primary mt-4" onClick={() => router.push(`/cars/${carId}`)}>Back to car</button>
        <BottomNav />
      </main>
    );
  }

  return (
    <main className="px-4 pb-24 pt-6">
      <button onClick={() => router.push(`/cars/${carId}`)} className="mb-4 text-sm text-gray-500 dark:text-gray-400">‹ Back</button>
      <h1 className="mb-1 text-2xl font-bold">Import service history</h1>
      <p className="mb-4 text-sm text-gray-500 dark:text-gray-400">
        Upload a PDF, Word, or Excel document with past service records — we&apos;ll pull out what we can, and you review it before anything is saved.
      </p>

      {error && <p className="mb-4 rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p>}

      {rows === null && (
        <form onSubmit={extract} className="card space-y-3">
          <div>
            <label className="label">Document</label>
            <input
              className="input"
              type="file"
              accept=".pdf,.docx,.xlsx"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
              required
            />
          </div>
          <button className="btn-primary" disabled={extracting || !file}>
            {extracting ? "Reading document…" : "Extract records"}
          </button>
        </form>
      )}

      {extracting && (
        <div className="flex justify-center py-10"><Spinner /></div>
      )}

      {rows !== null && rows.length === 0 && (
        <p className="card text-center text-sm text-gray-400 dark:text-gray-500">
          Couldn&apos;t find anything that looked like a service record in that document.
        </p>
      )}

      {rows !== null && rows.length > 0 && (
        <div className="space-y-3">
          <p className="text-[13px] font-semibold text-gray-500 dark:text-gray-400">
            Review before saving — {rows.filter((r) => r.include).length} of {rows.length} selected
          </p>
          {rows.map((row) => (
            <div key={row.rowId} className="card space-y-2">
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 text-sm font-semibold">
                  <input type="checkbox" checked={row.include} onChange={() => toggleInclude(row.rowId)} />
                  {row.kind === "part_purchase" ? "Part purchase" : "Service"}
                </label>
                {row.possible_duplicate && (
                  <span className="text-[12px] font-medium text-amber-600 dark:text-amber-400">Looks already logged</span>
                )}
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="label">Date</label>
                  <input className="input" type="date" value={row.date} onChange={update(row.rowId, "date")} />
                </div>
                <div>
                  <label className="label">Cost</label>
                  <input className="input" type="number" step="0.01" min="0" value={row.cost ?? ""} onChange={update(row.rowId, "cost")} />
                </div>
              </div>
              {row.kind === "service" && (
                <div>
                  <label className="label">Category</label>
                  <select className="input" value={row.service_type || "other"} onChange={update(row.rowId, "service_type")}>
                    {SERVICE_TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                </div>
              )}
              <div>
                <label className="label">{row.kind === "part_purchase" ? "Vendor" : "Garage"}</label>
                <input className="input" value={row.vendor} onChange={update(row.rowId, "vendor")} />
              </div>
              <div>
                <label className="label">Notes</label>
                <textarea className="input" rows={2} value={row.description} onChange={update(row.rowId, "description")} />
              </div>
            </div>
          ))}
          <button className="btn-primary" onClick={confirm} disabled={saving || rows.every((r) => !r.include)}>
            {saving ? "Saving…" : `Save ${rows.filter((r) => r.include).length} record(s)`}
          </button>
        </div>
      )}

      <BottomNav />
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <ImportHistory />
    </AuthGuard>
  );
}
