"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MdOutlineDirectionsCar, MdOutlineNotifications, MdOutlineReceiptLong, MdOutlineSettings } from "react-icons/md";

// `match` covers nested routes that belong to this tab (e.g. /cars/:id or
// /reminders/new) so they still highlight the right tab instead of none.
const ITEMS = [
  { href: "/dashboard", label: "Garage", Icon: MdOutlineDirectionsCar, match: ["/dashboard", "/cars"] },
  { href: "/reminders", label: "Reminders", Icon: MdOutlineNotifications, match: ["/reminders"] },
  { href: "/expenses", label: "Expenses", Icon: MdOutlineReceiptLong, match: ["/expenses"] },
  { href: "/settings", label: "Settings", Icon: MdOutlineSettings, match: ["/settings"] },
];

function isActive(pathname, prefixes) {
  return prefixes.some((prefix) => pathname === prefix || pathname?.startsWith(`${prefix}/`));
}

export default function BottomNav() {
  const pathname = usePathname();

  return (
    <div className="fixed inset-x-0 bottom-4 z-20 mx-auto max-w-lg px-4">
      <nav className="flex items-center justify-between gap-1 rounded-full border border-gray-200 bg-white/90 px-2 py-2 shadow-lg shadow-black/5 backdrop-blur dark:border-white/10 dark:bg-gray-900/90 dark:shadow-black/40">
        {ITEMS.map(({ href, label, Icon, match }) => {
          const active = isActive(pathname, match);
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
