"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Dancing_Script } from "next/font/google";
import {
  MdOutlineDirectionsCar,
  MdOutlineNotifications,
  MdOutlineReceiptLong,
  MdOutlineSmartToy,
} from "react-icons/md";
import { isLoggedIn } from "@/lib/api";

const brandFont = Dancing_Script({ subsets: ["latin"], weight: ["700"] });

const FEATURES = [
  {
    Icon: MdOutlineDirectionsCar,
    title: "Track every car you own",
    description: "Register as many cars as you like — service history, plate, VIN, odometer, and photos, all in one place.",
  },
  {
    Icon: MdOutlineNotifications,
    title: "Never miss a service",
    description: "Log a service once and GlavBox tracks the next one — by distance, by date, or whichever comes first.",
  },
  {
    Icon: MdOutlineReceiptLong,
    title: "Know what it costs you",
    description: "Every garage visit, fuel-up, and premium — see exactly what your car costs you, month by month.",
  },
  {
    Icon: MdOutlineSmartToy,
    title: "Ask your car anything",
    description: "A built-in assistant that knows your car's history — what's due, what it's cost you, what a trouble code means.",
  },
];

export default function LandingContent() {
  const router = useRouter();

  useEffect(() => {
    if (isLoggedIn()) router.replace("/dashboard");
  }, [router]);

  return (
    <main className="flex min-h-screen flex-col bg-[#04120c] text-white">
      {/* Hero */}
      <div className="relative h-[26rem] overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="https://res.cloudinary.com/soultech/image/upload/e_improve,w_900,h_700,c_fill,g_auto,q_auto,f_auto/v1784111131/MANSORY_P1100_Audi_RS6_Carbon_Turquoise_Madness_Part_2_zos9uq.jpg"
          alt=""
          width={900}
          height={700}
          fetchPriority="high"
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[#04120c] via-[#04120c]/20 to-[#0a1a14]" />
        <div className="absolute inset-x-0 top-0 h-56 bg-gradient-to-b from-black/80 via-black/40 to-transparent" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(52,211,153,0.4),transparent_55%)]" />
        <div className="relative flex h-full flex-col">
          <div className="flex justify-end p-4">
            <Link
              href="/login"
              className="rounded-full border border-white/25 bg-white/10 px-4 py-1.5 text-[13px] font-medium text-white backdrop-blur-sm transition active:scale-95"
            >
              Sign in
            </Link>
          </div>
          <div className="flex flex-1 flex-col items-center justify-start px-8 pt-4 text-center">
            <h1 className={`${brandFont.className} text-5xl font-bold tracking-wide text-white drop-shadow-[0_2px_10px_rgba(0,0,0,0.9)]`}>
              GlavBox
            </h1>
            <p className="mt-3 max-w-xs text-lg text-emerald-100/90 drop-shadow-[0_1px_6px_rgba(0,0,0,0.9)]">
              The glovebox for your car&apos;s paperwork.
            </p>
            <p className="mt-1 max-w-xs text-sm text-emerald-100/60 drop-shadow-[0_1px_6px_rgba(0,0,0,0.9)]">
              It never loses a receipt, and it reminds you before something&apos;s due.
            </p>
          </div>
        </div>
      </div>

      {/* Content sheet */}
      <div className="relative flex-1 rounded-t-[32px] bg-[#0a1a14] px-6 pb-10 pt-8 shadow-[0_-20px_60px_rgba(0,0,0,0.5)]">
        <Link
          href="/login?mode=signup"
          className="block w-full rounded-full bg-gradient-to-r from-emerald-400 to-green-500 px-4 py-3.5 text-center text-[15px] font-bold text-[#04120c] shadow-[0_8px_24px_rgba(52,211,153,0.35)] transition active:scale-[0.99]"
        >
          Get started
        </Link>

        <div className="mt-10 space-y-7">
          {FEATURES.map(({ Icon, title, description }) => (
            <div key={title} className="flex gap-4">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white/5 text-emerald-400">
                <Icon size={22} aria-hidden="true" />
              </span>
              <div>
                <p className="font-semibold text-white">{title}</p>
                <p className="mt-0.5 text-[13px] leading-relaxed text-white/50">{description}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-10 rounded-2xl bg-white/5 p-4 text-center">
          <p className="text-[13px] text-white/60">Your data is yours. We don&apos;t sell it, and there are no ads — ever.</p>
        </div>

        <div className="mt-8 border-t border-white/10 pt-6 text-center">
          <div className="flex items-center justify-center gap-3 text-[12px] font-medium text-white/50">
            <Link href="/privacy" className="underline underline-offset-2">
              Privacy &amp; Security
            </Link>
            <span className="text-white/20">·</span>
            <a
              href="https://x.com/GlavboxApp"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2"
            >
              @GlavboxApp
            </a>
          </div>
          <p className="mt-2 text-[12px] text-white/30">© {new Date().getFullYear()} GlavBox. All rights reserved.</p>
        </div>
      </div>
    </main>
  );
}
