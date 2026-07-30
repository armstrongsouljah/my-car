"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, downloadFile } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";

function ReportDetail() {
  const { period } = useParams(); // "2026-05"
  const router = useRouter();
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    api(`/expenses/reports/${period}/`)
      .then(setReport)
      .catch((err) => setError(err.message));
  }, [period]);

  async function handleDownload() {
    setDownloading(true);
    try {
      await downloadFile(`/expenses/reports/${period}/pdf/`, `glavbox-expenses-${period}.pdf`);
    } catch (err) {
      setError(err.message);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <main className="px-4 pb-24 pt-6">
      <button onClick={() => router.push("/expenses/reports")} className="mb-3 text-sm text-gray-400 dark:text-gray-500">
        ‹ All reports
      </button>

      {error && <p className="mb-4 rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p>}

      {report && (
        <>
          <h1 className="mb-4 text-2xl font-bold">{report.month_label}</h1>

          <div className="mb-4 grid grid-cols-2 gap-3">
            <div className="card">
              <p className="text-[12px] text-gray-400 dark:text-gray-500">Total spent</p>
              <p className="text-xl font-bold">{report.total.toLocaleString()}</p>
              {report.change_percent_vs_previous_month !== null && report.change_percent_vs_previous_month !== undefined && (
                <p className={`text-[12px] font-medium ${report.change_vs_previous_month > 0 ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"}`}>
                  {report.change_vs_previous_month > 0 ? "▲" : "▼"} {Math.abs(report.change_percent_vs_previous_month)}% vs last month
                </p>
              )}
            </div>
            <div className="card">
              <p className="text-[12px] text-gray-400 dark:text-gray-500">Expenses logged</p>
              <p className="text-xl font-bold">{report.count}</p>
            </div>
          </div>

          <button className="btn-primary mb-6 w-full" onClick={handleDownload} disabled={downloading}>
            {downloading ? "Preparing PDF…" : "Download PDF"}
          </button>

          <div className="card mb-4">
            <p className="mb-3 font-semibold">By category</p>
            {report.by_category.length === 0 && <p className="text-sm text-gray-400 dark:text-gray-500">Nothing logged this month.</p>}
            <div className="space-y-2">
              {report.by_category.map((row) => (
                <div key={row.category} className="flex items-center justify-between text-sm">
                  <p>{row.category_label}</p>
                  <p className="font-semibold">{row.total.toLocaleString()}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <p className="mb-3 font-semibold">By car</p>
            {report.by_car.length === 0 && <p className="text-sm text-gray-400 dark:text-gray-500">Nothing logged this month.</p>}
            <div className="space-y-2">
              {report.by_car.map((row) => (
                <div key={row.car_id} className="flex items-center justify-between text-sm">
                  <p>{row.label}</p>
                  <p className="font-semibold">{row.total.toLocaleString()}</p>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      <BottomNav />
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <ReportDetail />
    </AuthGuard>
  );
}
