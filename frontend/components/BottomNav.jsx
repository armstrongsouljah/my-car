"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MdOutlineDirectionsCar, MdOutlineNotifications, MdOutlineReceiptLong, MdOutlineSettings } from "react-icons/md";

const ITEMS = [
  ["/dashboard", "Garage", MdOutlineDirectionsCar],
  ["/reminders", "Reminders", MdOutlineNotifications],
  ["/expenses", "Expenses", MdOutlineReceiptLong],
  ["/settings", "Settings", MdOutlineSettings],
];

export default function BottomNav() {
  const pathname = usePathname();

  return (
    <div className="fixed inset-x-0 bottom-4 z-20 mx-auto max-w-lg px-4">
      <nav className="flex items-center justify-between gap-1 rounded-full border border-gray-200 bg-white/90 px-2 py-2 shadow-lg shadow-black/5 backdrop-blur dark:border-white/10 dark:bg-gray-900/90 dark:shadow-black/40">
        {ITEMS.map(([href, label, Icon]) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              aria-label={label}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-full py-2.5 text-[12px] font-medium transition-all ${
                active
                  ? "bg-gray-900 text-white dark:bg-white dark:text-gray-900"
                  : "text-gray-400 dark:text-gray-500"
              }`}
            >
              <Icon size={19} />
              {active && <span>{label}</span>}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
