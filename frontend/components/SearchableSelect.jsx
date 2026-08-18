"use client";

import { useEffect, useMemo, useRef, useState } from "react";

// Native <select><optgroup> has no way to cap its own dropdown height or add
// a search box (the "size" attribute forces an inline list box instead), so
// long grouped option lists (see #148) render at native height and can run
// off-screen. This swaps in a custom trigger + panel with a fixed max-height
// scroll area and a filter input, while keeping the same
// `groups: [{ label, options: [[value, label]] }]` shape ServiceForm already
// built for the <optgroup> rendering.
export default function SearchableSelect({ groups, value, onChange, placeholder = "Select…" }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef(null);
  const searchRef = useRef(null);

  const selectedLabel = useMemo(() => {
    for (const group of groups) {
      const match = group.options.find(([optValue]) => optValue === value);
      if (match) return match[1];
    }
    return placeholder;
  }, [groups, value, placeholder]);

  const filteredGroups = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return groups;
    return groups
      .map((group) => ({
        ...group,
        options: group.options.filter(([, label]) => label.toLowerCase().includes(needle)),
      }))
      .filter((group) => group.options.length > 0);
  }, [groups, query]);

  useEffect(() => {
    if (!open) return;
    searchRef.current?.focus();
    function onPointerDown(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    }
    function onKey(event) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function pick(optValue) {
    onChange(optValue);
    setOpen(false);
    setQuery("");
  }

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        className="input flex items-center justify-between text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="truncate">{selectedLabel}</span>
        <span className="ml-2 shrink-0 text-gray-400">▾</span>
      </button>
      {open && (
        <div className="absolute z-20 mt-1 w-full overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-900">
          <input
            ref={searchRef}
            className="input rounded-none border-x-0 border-t-0"
            placeholder="Search…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <div className="max-h-56 overflow-y-auto py-1">
            {filteredGroups.length === 0 && (
              <p className="px-4 py-3 text-sm text-gray-400">No matches</p>
            )}
            {filteredGroups.map((group) => (
              <div key={group.label}>
                <p className="px-4 pt-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-gray-400">
                  {group.label}
                </p>
                {group.options.map(([optValue, optLabel]) => (
                  <button
                    type="button"
                    key={optValue}
                    onClick={() => pick(optValue)}
                    className={`block w-full px-4 py-2 text-left text-[15px] hover:bg-gray-50 dark:hover:bg-gray-800 ${
                      optValue === value ? "font-semibold text-emerald-600 dark:text-emerald-400" : "text-gray-900 dark:text-gray-100"
                    }`}
                  >
                    {optLabel}
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
