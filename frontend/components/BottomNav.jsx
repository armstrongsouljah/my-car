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

// See #68 — full-width bar docked to the screen edge (rounded top corners
// only) with a sliding accent indicator, instead of the old floating pill
// whose active tab swapped color instantly and jumped width (icon+label vs.
// icon-only) on every switch.
export default function BottomNav() {
  const pathname = usePathname();
  const activeIndex = ITEMS.findIndex(({ match }) => isActive(pathname, match));

  return (
    <div className="fixed inset-x-0 bottom-0 z-20">
      <nav className="relative grid grid-cols-4 rounded-t-2xl border-t border-gray-200 bg-white/95 pb-[env(safe-area-inset-bottom)] shadow-lg shadow-black/5 backdrop-blur dark:border-white/10 dark:bg-gray-900/95 dark:shadow-black/40">
        {/* Absolutely positioned, so it's excluded from grid placement —
            slides between the 4 equal-width column slots by translating its
            own width (100%) times the active index. */}
        {activeIndex >= 0 && (
          <span
            aria-hidden="true"
            className="pointer-events-none absolute top-0 h-[3px] w-1/4 rounded-full bg-brand transition-transform duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] motion-reduce:transition-none"
            style={{ transform: `translateX(${activeIndex * 100}%)` }}
          />
        )}
        {ITEMS.map(({ href, label, Icon, match }, index) => {
          const active = index === activeIndex;
          return (
            <Link
              key={href}
              href={href}
              aria-label={label}
              aria-current={active ? "page" : undefined}
              className="flex flex-col items-center justify-center gap-1 py-2.5 text-[11px] font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand"
            >
              <Icon
                size={20}
                className={`transition-all duration-300 motion-reduce:transition-none ${
                  active ? "-translate-y-0.5 scale-110 text-brand" : "text-gray-400 dark:text-gray-500"
                }`}
              />
              <span
                className={`transition-colors duration-300 motion-reduce:transition-none ${
                  active ? "text-brand" : "text-gray-400 dark:text-gray-500"
                }`}
              >
                {label}
              </span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
