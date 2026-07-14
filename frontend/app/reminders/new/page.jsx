"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import FilterChips from "@/components/FilterChips";
import TrackingMethodPicker from "@/components/TrackingMethodPicker";
import ReminderDetailsForm from "@/components/ReminderDetailsForm";

const FILTERS = [
  { value: "all", label: "All" },
  { value: "maintenance", label: "Maintenance" },
  { value: "documentation", label: "Documents" },
  { value: "essential", label: "Essential Reminders" },
];

const CATEGORY_LABELS = { maintenance: "Maintenance", documentation: "Documentation", other: "Other" };

const CUSTOM_ITEM = {
  key: "", title: "Custom reminder", category: "other", is_essential: false,
  icon: "⚙️", description: "Create a reminder for anything not already covered by the preset list.",
  suggested_method: null, default_interval_km: null, default_interval_months: null, suggestion_note: null,
};

function AddReminder() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const carId = searchParams.get("car");

  const [car, setCar] = useState(null);
  const [catalog, setCatalog] = useState(null);
  const [error, setError] = useState("");
  const [step, setStep] = useState("browse"); // browse | method | details
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState(null);
  const [trackingMethod, setTrackingMethod] = useState("date_and_mileage");

  useEffect(() => {
    if (!carId) return;
    api(`/cars/${carId}/`).then(setCar).catch((err) => setError(err.message));
    api("/reminders/catalog/").then(setCatalog).catch((err) => setError(err.message));
  }, [carId]);

  const grouped = useMemo(() => {
    if (!catalog) return [];
    const items = catalog.items.filter((item) => {
      const matchesSearch = item.title.toLowerCase().includes(search.toLowerCase());
      const matchesFilter =
        filter === "all" ? true : filter === "essential" ? item.is_essential : item.category === filter;
      return matchesSearch && matchesFilter;
    });

    const byCategory = {};
    for (const item of items) {
      byCategory[item.category] = byCategory[item.category] || [];
      byCategory[item.category].push(item);
    }
    if (!search) {
      byCategory.other = [...(byCategory.other || []), CUSTOM_ITEM];
    }

    return Object.entries(byCategory).filter(([, list]) => list.length > 0);
  }, [catalog, search, filter]);

  function pick(item) {
    setSelected(item);
    setTrackingMethod(item.suggested_method || "date_and_mileage");
    setStep("method");
  }

  function back() {
    if (step === "browse") router.back();
    else if (step === "method") setStep("browse");
    else setStep("method");
  }

  if (!carId) {
    return <main className="p-6 text-sm text-gray-400">No car selected.</main>;
  }
  if (error) return <main className="p-6"><p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p></main>;
  if (!car || !catalog) return <main className="p-6 text-sm text-gray-400">Loading…</main>;

  return (
    <main className="px-4 pb-24 pt-6">
      <button onClick={back} className="mb-4 text-sm text-gray-500">‹ Back</button>

      {step === "browse" && (
        <>
          <h1 className="mb-4 text-2xl font-bold">What to remind?</h1>
          <input
            className="input mb-3"
            placeholder="Search reminders"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <div className="mb-4">
            <FilterChips options={FILTERS} value={filter} onChange={setFilter} />
          </div>

          <div className="space-y-5">
            {grouped.map(([category, items]) => (
              <div key={category}>
                <p className="mb-2 text-[13px] font-semibold text-gray-500">{CATEGORY_LABELS[category] || category}</p>
                <div className="space-y-2">
                  {items.map((item) => (
                    <button key={item.key || "custom"} onClick={() => pick(item)} className="card flex w-full items-center gap-3 text-left">
                      <span className="text-2xl">{item.icon}</span>
                      <span className="flex-1">
                        {item.is_essential && <span className="block text-[12px] font-semibold text-blue-600">Essential Reminder</span>}
                        <span className="block font-semibold">{item.title}</span>
                        <span className="block text-[13px] text-gray-500">{item.description}</span>
                      </span>
                      <span className="text-gray-300">›</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {grouped.length === 0 && <p className="text-center text-sm text-gray-400">No reminders match your search.</p>}
          </div>
        </>
      )}

      {step === "method" && selected && (
        <>
          <h1 className="mb-1 text-2xl font-bold">{selected.title || "Custom reminder"}</h1>
          <p className="mb-4 text-sm text-gray-500">How should we remind you?</p>
          <TrackingMethodPicker
            value={trackingMethod}
            onChange={setTrackingMethod}
            suggested={selected.suggested_method}
            suggestionNote={selected.suggestion_note}
          />
          <button className="btn-primary mt-4" onClick={() => setStep("details")}>Next</button>
        </>
      )}

      {step === "details" && selected && (
        <>
          <h1 className="mb-4 text-2xl font-bold">{selected.title || "Custom reminder"}</h1>
          <ReminderDetailsForm
            car={car}
            preset={selected.key ? selected : null}
            trackingMethod={trackingMethod}
            onSaved={() => router.replace("/reminders")}
          />
        </>
      )}

      <BottomNav />
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <Suspense fallback={<main className="p-6 text-sm text-gray-400">Loading…</main>}>
        <AddReminder />
      </Suspense>
    </AuthGuard>
  );
}
