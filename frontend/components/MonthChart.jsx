"use client";

import { useState } from "react";
import { formatAmount, formatAmountCompact } from "@/lib/currency";
import { CATEGORIES, CATEGORY_COLOR_CLASS } from "@/lib/expenseCategories";

const BAR_AREA_HEIGHT = 100; // px — the bar's own max height inside the chart's 150px row

export function monthLabel(iso) {
  return new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short", year: "2-digit" });
}

function YearNav({ year, onPrevYear, onNextYear, canGoPrev, canGoNext }) {
  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={onPrevYear}
        disabled={!canGoPrev}
        aria-label="Previous year"
        className="flex h-6 w-6 items-center justify-center rounded-full text-gray-400 outline-none transition hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-brand disabled:opacity-30 disabled:hover:bg-transparent dark:text-gray-500 dark:hover:bg-gray-800"
      >
        ‹
      </button>
      <span className="w-10 text-center text-[13px] font-medium tabular-nums">{year}</span>
      <button
        type="button"
        onClick={onNextYear}
        disabled={!canGoNext}
        aria-label="Next year"
        className="flex h-6 w-6 items-center justify-center rounded-full text-gray-400 outline-none transition hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-brand disabled:opacity-30 disabled:hover:bg-transparent dark:text-gray-500 dark:hover:bg-gray-800"
      >
        ›
      </button>
    </div>
  );
}

// onPrevYear/onNextYear are optional — omitting them (e.g. a compact
// dashboard glance, see #63) renders a static year instead of nav arrows,
// rather than forcing every caller to wire up year-browsing state.
export default function MonthChart({ months, currency, year, onPrevYear, onNextYear, canGoPrev, canGoNext }) {
  const [selectedKey, setSelectedKey] = useState(null);
  const showNav = typeof onPrevYear === "function";

  const hasData = !!months?.length;
  const max = hasData ? Math.max(...months.map((m) => m.total), 1) : 1;
  // Only legend/detail categories that actually appear somewhere in the
  // visible range — no point listing all 7 fixed categories if this car
  // has never had e.g. an insurance expense.
  const activeCategories = hasData ? CATEGORIES.filter(([key]) => months.some((m) => (m.by_category?.[key] || 0) > 0)) : [];
  const selectedMonth = hasData ? months.find((m) => m.month === selectedKey) || months[months.length - 1] : null;

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <p className="font-semibold">Month on month</p>
        {showNav ? (
          <YearNav year={year} onPrevYear={onPrevYear} onNextYear={onNextYear} canGoPrev={canGoPrev} canGoNext={canGoNext} />
        ) : (
          <span className="text-[13px] font-medium tabular-nums text-gray-400 dark:text-gray-500">{year}</span>
        )}
      </div>

      {!hasData && (
        <p className="py-10 text-center text-[13px] text-gray-400 dark:text-gray-500">No expenses logged in {year}.</p>
      )}

      {hasData && (
        <>
          {activeCategories.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-x-3 gap-y-1.5">
              {activeCategories.map(([key, label]) => (
                <span key={key} className="flex items-center gap-1.5 text-[11px] text-gray-500 dark:text-gray-400">
                  <span className={`h-2 w-2 rounded-full ${CATEGORY_COLOR_CLASS[key]}`} />
                  {label}
                </span>
              ))}
            </div>
          )}

          <div className="flex items-end gap-1 overflow-x-auto pb-1" style={{ height: 150 }}>
            {months.map((month) => {
              const isSelected = month.month === selectedMonth.month;
              const segments = CATEGORIES
                .map(([key]) => [key, month.by_category?.[key] || 0])
                .filter(([, value]) => value > 0);
              // Pixels, not a percentage: this div's immediate parent (the
              // button) has no defined height of its own (items-end, not
              // stretch), so a percentage height here would resolve against
              // "auto" and collapse to 0 — see #58.
              const barHeight = Math.max((month.total / max) * BAR_AREA_HEIGHT, 2);

              return (
                <button
                  type="button"
                  key={month.month}
                  onClick={() => setSelectedKey(month.month)}
                  onFocus={() => setSelectedKey(month.month)}
                  aria-pressed={isSelected}
                  aria-label={`${monthLabel(month.month)}: ${formatAmount(month.total, currency)}`}
                  className={`flex min-w-[32px] flex-1 flex-col items-center justify-end gap-1 rounded-lg pt-2 outline-none transition ${
                    isSelected ? "bg-brand/10" : "hover:bg-gray-100 dark:hover:bg-gray-800/60"
                  }`}
                >
                  {/* Compact (10k/1m, see #125) -- full precision stays in
                      aria-label above and the selected-month detail panel
                      below, where there's room for it. */}
                  <p className="text-[10px] font-medium text-gray-500 dark:text-gray-400">
                    {formatAmountCompact(Math.round(month.total), currency)}
                  </p>
                  <div
                    className="flex w-full max-w-[24px] flex-col justify-end gap-[2px] overflow-hidden rounded-t-[4px]"
                    style={{ height: barHeight }}
                  >
                    {segments.length === 0 ? (
                      <div className="w-full flex-1 bg-gray-200 dark:bg-gray-700" />
                    ) : (
                      segments.map(([key, value]) => (
                        <div
                          key={key}
                          className={`w-full ${CATEGORY_COLOR_CLASS[key]}`}
                          style={{ flexGrow: value, flexBasis: 0 }}
                        />
                      ))
                    )}
                  </div>
                  <p className="text-[10px] text-gray-400 dark:text-gray-500">{monthLabel(month.month)}</p>
                </button>
              );
            })}
          </div>

          <div className="mt-3 rounded-xl bg-gray-50 p-3 dark:bg-gray-800/60">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-[13px] font-semibold">{monthLabel(selectedMonth.month)}</p>
              <p className="text-[13px] font-bold">{formatAmount(selectedMonth.total, currency)}</p>
            </div>
            {selectedMonth.total === 0 ? (
              <p className="text-[12px] text-gray-400 dark:text-gray-500">No expenses logged.</p>
            ) : (
              <div className="space-y-1.5">
                {CATEGORIES.filter(([key]) => (selectedMonth.by_category?.[key] || 0) > 0).map(([key, label]) => (
                  <div key={key} className="flex items-center justify-between text-[12px]">
                    <span className="flex items-center gap-1.5 text-gray-600 dark:text-gray-300">
                      <span className={`h-2 w-2 rounded-full ${CATEGORY_COLOR_CLASS[key]}`} />
                      {label}
                    </span>
                    <span className="font-medium text-gray-900 dark:text-gray-100">
                      {formatAmount(selectedMonth.by_category[key], currency)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
