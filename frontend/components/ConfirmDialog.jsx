"use client";

import { useEffect, useRef } from "react";

/**
 * Mobile-friendly confirmation sheet — slides up from the bottom with a
 * dimmed backdrop, replacing the browser's default confirm() dialog.
 */
export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  loading = false,
  onConfirm,
  onCancel,
}) {
  const confirmRef = useRef(null);
  const previouslyFocused = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event) => event.key === "Escape" && !loading && onCancel?.();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    previouslyFocused.current = document.activeElement;
    confirmRef.current?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      previouslyFocused.current?.focus?.();
    };
  }, [open, loading, onCancel]);

  if (!open) return null;

  const dismiss = () => !loading && onCancel?.();

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center" role="dialog" aria-modal="true">
      <button
        aria-label="Close"
        onClick={dismiss}
        className="absolute inset-0 bg-black/40 backdrop-blur-[2px] transition-opacity"
      />
      <div className="relative z-10 w-full max-w-lg animate-[slideUp_.2s_ease-out] rounded-t-3xl bg-white p-6 pb-8 shadow-2xl dark:bg-gray-900 sm:max-w-sm sm:rounded-3xl sm:pb-6">
        <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-gray-200 dark:bg-gray-700 sm:hidden" />
        <div
          className={`mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full text-2xl ${
            destructive ? "bg-red-50 dark:bg-red-500/10" : "bg-gray-100 dark:bg-gray-800"
          }`}
        >
          {destructive ? "🗑️" : "❓"}
        </div>
        <h2 className="text-center text-lg font-bold">{title}</h2>
        <p className="mt-2 text-center text-sm text-gray-500 dark:text-gray-400">{message}</p>
        <div className="mt-6 space-y-2">
          <button
            ref={confirmRef}
            onClick={onConfirm}
            disabled={loading}
            className={`w-full rounded-xl px-4 py-3 text-[15px] font-semibold text-white active:scale-[0.99] disabled:opacity-50 ${
              destructive ? "bg-red-600" : "bg-gray-900 dark:bg-white dark:text-gray-900"
            }`}
          >
            {loading ? "Please wait…" : confirmLabel}
          </button>
          <button onClick={dismiss} disabled={loading} className="btn-secondary">
            {cancelLabel}
          </button>
        </div>
      </div>
      <style jsx global>{`
        @keyframes slideUp {
          from { transform: translateY(24px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
