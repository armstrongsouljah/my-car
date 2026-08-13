"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import FilterChips from "@/components/FilterChips";
import Spinner from "@/components/Spinner";
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

  // Only fetched when no ?car= is given -- lets this page double as a car
  // picker (#133) instead of dead-ending, for the multi-car case where the
  // Reminders page's single "+ Add reminder" button can't already know
  // which car you mean.
  const [pickerCars, setPickerCars] = useState(null);

  useEffect(() => {
    // Reset the whole creation flow on every carId change, not just refetch
    // -- otherwise switching cars via the in-page picker (browse A, back,
    // pick B) can leave step/selected/trackingMethod from car A dangling,
    // and ReminderDetailsForm would save car B's reminder using car A's
    // stale preset/tracking choice.
    let ignore = false;
    setCar(null);
    setCatalog(null);
    setStep("browse");
    setSelected(null);
    setTrackingMethod("date_and_mileage");
    setError("");

    if (!carId) {
      api("/cars/")
        .then((data) => { if (!ignore) setPickerCars(data.results || data); })
        .catch((err) => { if (!ignore) setError(err.message); });
      return () => { ignore = true; };
    }
    api(`/cars/${carId}/`)
      .then((data) => { if (!ignore) setCar(data); })
      .catch((err) => { if (!ignore) setError(err.message); });
    api("/reminders/catalog/")
      .then((data) => { if (!ignore) setCatalog(data); })
      .catch((err) => { if (!ignore) setError(err.message); });
    return () => { ignore = true; };
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
    if (!search && filter === "all") {
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
    // A real picker (#133), not just a dead end back to /reminders -- the
    // Reminders page's single "+ Add reminder" button lands here whenever
    // it can't already tell which car you mean (more than one car).
    // BottomNav isn't rendered on this branch (this is a modal-ish flow,
    // same as the carId-present view below), so the explicit "‹ Back" is
    // the only way out -- kept visible across loading/error/empty too.
    return (
      <main className="px-4 pb-24 pt-6">
        <button onClick={() => router.push("/reminders")} className="mb-4 text-sm text-gray-500 dark:text-gray-400">‹ Back</button>

        {error ? (
          <p className="rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p>
        ) : !pickerCars ? (
          <div className="flex justify-center p-10"><Spinner /></div>
        ) : (
          <>
            <h1 className="mb-4 text-2xl font-bold">Which car?</h1>
            {pickerCars.length === 0 ? (
              <p className="text-center text-sm text-gray-400 dark:text-gray-500">Add a car first to set up reminders for it.</p>
            ) : (
              <div className="space-y-2">
                {pickerCars.map((entry) => (
                  <button
                    key={entry.id}
                    onClick={() => router.push(`/reminders/new?car=${entry.id}`)}
                    className="card flex w-full items-center justify-between gap-3 text-left"
                  >
                    <div>
                      <p className="font-semibold">
                        {entry.make} {entry.model}{entry.year ? ` (${entry.year})` : ""}
                      </p>
                      <p className="text-[13px] text-gray-500 dark:text-gray-400">
                        {entry.registration_number || "No plate"} · {Number(entry.current_odometer_km).toLocaleString()} km
                      </p>
                    </div>
                    <span className="text-gray-300 dark:text-gray-600">›</span>
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </main>
    );
  }
  if (error) return <main className="p-6"><p className="rounded-xl bg-red-50 dark:bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">{error}</p></main>;
  if (!car || !catalog) return <main className="flex justify-center p-10"><Spinner /></main>;

  return (
    <main className="px-4 pb-24 pt-6">
      <button onClick={back} className="mb-4 text-sm text-gray-500 dark:text-gray-400">‹ Back</button>

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
                <p className="mb-2 text-[13px] font-semibold text-gray-500 dark:text-gray-400">{CATEGORY_LABELS[category] || category}</p>
                <div className="space-y-2">
                  {items.map((item) => (
                    <button key={item.key || "custom"} onClick={() => pick(item)} className="card flex w-full items-center gap-3 text-left">
                      <span className="text-2xl">{item.icon}</span>
                      <span className="flex-1">
                        {item.is_essential && <span className="block text-[12px] font-semibold text-blue-600 dark:text-blue-400">Essential Reminder</span>}
                        <span className="block font-semibold">{item.title}</span>
                        <span className="block text-[13px] text-gray-500 dark:text-gray-400">{item.description}</span>
                      </span>
                      <span className="text-gray-300 dark:text-gray-600">›</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {grouped.length === 0 && <p className="text-center text-sm text-gray-400 dark:text-gray-500">No reminders match your search.</p>}
          </div>
        </>
      )}

      {step === "method" && selected && (
        <>
          <h1 className="mb-1 text-2xl font-bold">{selected.title || "Custom reminder"}</h1>
          <p className="mb-4 text-sm text-gray-500 dark:text-gray-400">How should we remind you?</p>
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
      <Suspense fallback={<main className="flex justify-center p-10"><Spinner /></main>}>
        <AddReminder />
      </Suspense>
    </AuthGuard>
  );
}
