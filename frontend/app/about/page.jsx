"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

function Section({ icon, title, children }) {
  return (
    <section className="card space-y-2">
      <h2 className="flex items-center gap-2 font-semibold">
        <span className="text-lg" aria-hidden="true">{icon}</span> {title}
      </h2>
      <div className="space-y-2 text-sm leading-relaxed text-gray-600 dark:text-gray-400">{children}</div>
    </section>
  );
}

export default function AboutPage() {
  const router = useRouter();

  function goBack() {
    // router.back() is a no-op if this page was opened directly (no
    // in-app history to return to) — fall back to the login screen.
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
    } else {
      router.push("/");
    }
  }

  return (
    <main className="space-y-4 px-4 pb-12 pt-6">
      <button onClick={goBack} className="mb-1 text-sm text-gray-500 dark:text-gray-400">‹ Back</button>

      <div>
        <h1 className="text-2xl font-bold">What is GlavBox?</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Think of it as the glovebox for your car&apos;s paperwork — except it never loses a receipt, and it reminds
          you before something&apos;s due.
        </p>
      </div>

      <Section icon="🚗" title="Track every car you own">
        <p>
          Register as many cars as you like — one at a time, or several in one go if you&apos;re setting up a whole
          household&apos;s garage. Keep make, model, plate, VIN, odometer, and a photo all in one place.
        </p>
      </Section>

      <Section icon="🔔" title="Never miss a service">
        <p>
          Log a service with a &ldquo;whichever comes first&rdquo; interval — say, 5,000 km or 6 months — and GlavBox
          tracks it for you. You&apos;ll see it coming as due soon, then overdue, without digging through old receipts.
        </p>
        <p>
          General inspections get the same treatment. And we give new cars a couple of weeks&apos; grace period before
          nudging you about a first service or inspection — no instant nagging the day you sign up.
        </p>
      </Section>

      <Section icon="💸" title="Know what your car actually costs you">
        <p>
          Log garage visits, fuel, insurance, parts, tax — whatever you spend on it — and see month-on-month totals
          and category breakdowns. Log a costed service once and it shows up as an expense automatically, no
          re-typing the amount.
        </p>
      </Section>

      <Section icon="💬" title="Ask your car anything">
        <p>
          The built-in assistant can answer questions about a specific car — what&apos;s due, what it&apos;s cost you so
          far, what a trouble code means — grounded in the history you&apos;ve actually logged, not a guess.
        </p>
      </Section>

      <div className="card space-y-3 text-center">
        <p className="text-sm text-gray-600 dark:text-gray-400">Ready to set up your garage?</p>
        <Link href="/" className="btn-primary inline-block">Get started</Link>
      </div>

      <p className="pt-2 text-center text-[12px] text-gray-600 dark:text-gray-400">
        <Link href="/privacy" className="underline underline-offset-2">Privacy &amp; Security</Link>
      </p>
    </main>
  );
}
