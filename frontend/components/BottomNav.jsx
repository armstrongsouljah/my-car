"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function BottomNav() {
  const pathname = usePathname();

  const item = (href, label, icon) => (
    <Link
      href={href}
      className={`flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] font-medium ${
        pathname === href ? "text-gray-900 dark:text-white" : "text-gray-400 dark:text-gray-600"
      }`}
    >
      <span className="text-xl leading-none">{icon}</span>
      {label}
    </Link>
  );

  return (
    <nav className="fixed inset-x-0 bottom-0 z-20 mx-auto flex w-full max-w-lg border-t border-gray-200 bg-white/95 backdrop-blur dark:border-gray-800 dark:bg-gray-950/95">
      {item("/dashboard", "Garage", "🚗")}
      {item("/reminders", "Reminders", "🔔")}
      {item("/expenses", "Expenses", "💸")}
      {item("/settings", "Settings", "⚙️")}
    </nav>
  );
}
