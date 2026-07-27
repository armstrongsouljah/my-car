"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { MdOutlineDeleteOutline, MdOutlineFactCheck, MdOutlineMailOutline, MdOutlineShield, MdOutlineVpnKey } from "react-icons/md";

function Section({ Icon, title, children }) {
  return (
    <section className="card space-y-2">
      <h2 className="flex items-center gap-2 font-semibold">
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300">
          <Icon size={17} aria-hidden="true" />
        </span>
        {title}
      </h2>
      <div className="space-y-2 text-sm leading-relaxed text-gray-600 dark:text-gray-400">{children}</div>
    </section>
  );
}

export default function PrivacyPage() {
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
        <h1 className="text-2xl font-bold">Privacy &amp; Security</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          The short version: your data is yours. We keep it safe, we don&apos;t sell it, and we don&apos;t use it to make
          money off you in any way. Here&apos;s exactly how that works.
        </p>
      </div>

      <Section Icon={MdOutlineShield} title="Your data is safe with us">
        <p>
          GlavBox exists to help you take care of your car — not to profit from your information. We will never
          sell, rent, or trade your data to advertisers, data brokers, or anyone else. There are no ads in this app
          and there never will be.
        </p>
        <p>
          Everything you enter — your cars, service history, expenses, and reminders — is used for exactly one
          purpose: showing it back to you, in a useful way, when you need it.
        </p>
      </Section>

      <Section Icon={MdOutlineFactCheck} title="What we collect, and why">
        <p>Just what&apos;s needed to run the app well:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li><span className="font-medium text-gray-700 dark:text-gray-300">Account info</span> — your email and name, so you can sign in and we can reach you about your account.</li>
          <li><span className="font-medium text-gray-700 dark:text-gray-300">The car data you log</span> — service history, expenses, reminders, and photos, so the app can track intervals and remind you before something&apos;s due.</li>
          <li><span className="font-medium text-gray-700 dark:text-gray-300">Basic usage analytics</span> — which screens get used, so we know what to improve. This is aggregated and never sold.</li>
        </ul>
        <p>
          If you use the in-app assistant, your question and the relevant car details (service history, expenses,
          odometer) are sent to Google&apos;s Gemini API to generate an answer grounded in your own data. We don&apos;t
          store that data anywhere beyond your chat history, and we don&apos;t use it for anything else — that request
          is handled under Google&apos;s own API terms, which we&apos;d encourage you to check if you want the full
          picture of how they process it.
        </p>
      </Section>

      <Section Icon={MdOutlineVpnKey} title="Keep your account safe">
        <p>Your password is the main thing standing between your data and anyone else. A few habits that go a long way:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>Use a <span className="font-medium text-gray-700 dark:text-gray-300">strong, unique password</span> — at least 8 characters, ideally generated or unrelated to your other logins.</li>
          <li>Don&apos;t share it with anyone you don&apos;t fully trust — not a mechanic, not a family member borrowing the app, nobody.</li>
          <li>We will <span className="font-medium text-gray-700 dark:text-gray-300">never</span> ask for your password by email, chat, or phone. If someone does, it isn&apos;t us.</li>
        </ul>
        <p>You can change your password any time from Settings.</p>
      </Section>

      <Section Icon={MdOutlineDeleteOutline} title="Deleting your data">
        <p>
          You&apos;re in control. Deactivate your account any time from Settings — you&apos;ll be signed out everywhere and
          logins will be disabled immediately.
        </p>
        <p>
          For <span className="font-medium text-gray-700 dark:text-gray-300">60 days</span> after deactivation, your
          account is kept on hold in case you change your mind — reply to any email we&apos;ve sent you and we can
          reactivate it. After 60 days, it&apos;s permanently and irreversibly deleted, along with every car, service
          record, and expense on it.
        </p>
      </Section>

      <Section Icon={MdOutlineMailOutline} title="Questions?">
        <p>
          If anything here is unclear or you want your data handled differently, just reply to any email from
          GlavBox — a verification code, a reminder, whatever&apos;s in your inbox — and it&apos;ll reach us.
        </p>
      </Section>

      <p className="pt-2 text-center text-[12px] text-gray-600 dark:text-gray-400">
        <Link href="/settings" className="underline underline-offset-2">Back to Settings</Link>
      </p>
    </main>
  );
}
