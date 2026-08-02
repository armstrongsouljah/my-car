"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Dancing_Script } from "next/font/google";
import { MdOutlineAttachFile, MdOutlineClose, MdOutlineMarkEmailRead } from "react-icons/md";
import { api, getUser } from "@/lib/api";

const brandFont = Dancing_Script({ subsets: ["latin"], weight: ["700"] });

const SUBJECTS = [
  ["general_account", "General Account"],
  ["app_inquiry", "App Inquiry"],
  ["feature_suggestion", "Feature Suggestions"],
  ["other", "Other"],
];

const MAX_ATTACHMENTS = 5;
const MAX_ATTACHMENT_SIZE_MB = 10;
const REDIRECT_DELAY_MS = 3000;

// Deliberately starts empty rather than reading getUser() here: this runs
// during SSR too (client components still render server-side for the initial
// HTML), where getUser() always returns null, so seeding it with the actual
// stored user would mismatch the server-rendered markup a logged-in browser
// hydrates against. Prefilled in a useEffect below instead — client-only, by
// definition after the mismatch-sensitive hydration pass has already happened.
function initialForm() {
  return { name: "", email: "", subject: "general_account", custom_subject: "", message: "" };
}

function Hero({ tagline }) {
  return (
    <div className="relative h-56 overflow-hidden">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="https://res.cloudinary.com/soultech/image/upload/e_improve,w_900,h_700,c_fill,g_auto,q_auto,f_auto/v1784111131/MANSORY_P1100_Audi_RS6_Carbon_Turquoise_Madness_Part_2_zos9uq.jpg"
        alt=""
        className="absolute inset-0 h-full w-full object-cover"
      />
      <div className="absolute inset-0 bg-gradient-to-b from-[#04120c] via-[#04120c]/20 to-[#0a1a14]" />
      <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-black/80 via-black/40 to-transparent" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(52,211,153,0.4),transparent_55%)]" />
      <div className="relative flex h-full flex-col items-center justify-start pt-12">
        <h1 className={`${brandFont.className} text-4xl font-bold tracking-wide text-white drop-shadow-[0_2px_10px_rgba(0,0,0,0.9)]`}>
          GlavBox
        </h1>
        <p className="mt-0.5 text-sm text-emerald-100/80 drop-shadow-[0_1px_6px_rgba(0,0,0,0.9)]">{tagline}</p>
      </div>
    </div>
  );
}

function SentScreen() {
  const router = useRouter();

  useEffect(() => {
    const timer = setTimeout(() => router.replace("/login"), REDIRECT_DELAY_MS);
    return () => clearTimeout(timer);
  }, [router]);

  return (
    <main className="flex min-h-screen flex-col bg-[#04120c] text-white">
      <Hero tagline="Message sent" />
      <div className="relative flex flex-1 flex-col items-center justify-center gap-3 rounded-t-[32px] bg-[#0a1a14] px-6 pb-10 pt-8 text-center shadow-[0_-20px_60px_rgba(0,0,0,0.5)]">
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-400/10 text-emerald-400">
          <MdOutlineMarkEmailRead size={28} aria-hidden="true" />
        </span>
        <h2 className="text-xl font-bold">Message sent</h2>
        <p className="max-w-xs text-sm text-white/50">
          Thanks for reaching out — we&apos;ve got your message and will get back to you soon.
        </p>
        <p className="mt-2 text-sm text-white/40">
          Taking you back to sign in…{" "}
          <Link href="/login" className="font-semibold text-emerald-400">
            Go now
          </Link>
        </p>
      </div>
    </main>
  );
}

export default function ContactForm() {
  const router = useRouter();
  const [form, setForm] = useState(initialForm);
  const [files, setFiles] = useState([]);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  useEffect(() => {
    const user = getUser();
    if (!user) return;
    const name = [user.first_name, user.last_name].filter(Boolean).join(" ");
    setForm((prev) => ({ ...prev, name: name || prev.name, email: user.email || prev.email }));
  }, []);

  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  function goBack() {
    if (typeof window !== "undefined" && window.history.length > 1) router.back();
    else router.push("/login");
  }

  function addFiles(event) {
    const picked = Array.from(event.target.files || []);
    event.target.value = "";
    if (!picked.length) return;

    if (files.length + picked.length > MAX_ATTACHMENTS) {
      setError(`Please attach at most ${MAX_ATTACHMENTS} files.`);
      return;
    }
    const tooBig = picked.find((f) => f.size > MAX_ATTACHMENT_SIZE_MB * 1024 * 1024);
    if (tooBig) {
      setError(`"${tooBig.name}" is larger than ${MAX_ATTACHMENT_SIZE_MB}MB.`);
      return;
    }

    setError("");
    setFiles([...files, ...picked]);
  }

  function removeFile(index) {
    setFiles(files.filter((_, i) => i !== index));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSending(true);

    try {
      const body = new FormData();
      body.append("name", form.name);
      body.append("email", form.email);
      body.append("subject", form.subject);
      body.append("custom_subject", form.custom_subject);
      body.append("message", form.message);
      files.forEach((file) => body.append("attachments", file));

      await api("/support/", { method: "POST", body, isForm: true });
      setSent(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  if (sent) return <SentScreen />;

  return (
    <main className="flex min-h-screen flex-col bg-[#04120c] text-white">
      <Hero tagline="We're here to help" />

      <div className="relative flex-1 rounded-t-[32px] bg-[#0a1a14] px-6 pb-10 pt-8 shadow-[0_-20px_60px_rgba(0,0,0,0.5)]">
        <button onClick={goBack} className="mb-4 text-sm text-white/40">‹ Back</button>

        <h2 className="text-xl font-bold">Contact support</h2>
        <p className="mt-1 mb-6 text-sm text-white/50">
          Trouble activating your account, a general question, or feedback on the app — tell us what&apos;s up and
          we&apos;ll reply by email.
        </p>

        {error && <p className="mb-4 rounded-xl bg-red-400/10 p-3 text-sm text-red-300">{error}</p>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="auth-label" htmlFor="name">Name</label>
              <input id="name" className="auth-input" required value={form.name} onChange={update("name")} />
            </div>
            <div>
              <label className="auth-label" htmlFor="email">Email</label>
              <input id="email" className="auth-input" type="email" required value={form.email} onChange={update("email")} />
            </div>
          </div>

          <div>
            <label className="auth-label" htmlFor="subject">Subject</label>
            <select id="subject" className="auth-input" value={form.subject} onChange={update("subject")}>
              {SUBJECTS.map(([value, label]) => (
                <option key={value} value={value} className="bg-[#0a1a14]">{label}</option>
              ))}
            </select>
          </div>

          {form.subject === "other" && (
            <div>
              <label className="auth-label" htmlFor="custom_subject">What&apos;s it about?</label>
              <input
                id="custom_subject"
                className="auth-input"
                required
                placeholder="A short subject line"
                value={form.custom_subject}
                onChange={update("custom_subject")}
              />
            </div>
          )}

          <div>
            <label className="auth-label" htmlFor="message">Message</label>
            <textarea
              id="message"
              className="auth-input min-h-32 resize-y"
              required
              placeholder="Tell us what's going on…"
              value={form.message}
              onChange={update("message")}
            />
          </div>

          <div>
            <p className="auth-label">Attachments (optional)</p>
            <label className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-2xl border border-dashed border-white/15 bg-white/5 px-4 py-3 text-[13px] font-medium text-white/50">
              <MdOutlineAttachFile size={17} />
              Add files (up to {MAX_ATTACHMENTS}, {MAX_ATTACHMENT_SIZE_MB}MB each)
              <input type="file" multiple className="hidden" onChange={addFiles} />
            </label>

            {files.length > 0 && (
              <ul className="mt-2 space-y-1.5">
                {files.map((file, index) => (
                  <li key={`${file.name}-${index}`} className="flex items-center justify-between gap-2 rounded-lg bg-white/5 px-3 py-2 text-[13px] text-white/70">
                    <span className="truncate">{file.name}</span>
                    <button type="button" onClick={() => removeFile(index)} aria-label={`Remove ${file.name}`} className="text-white/40 hover:text-white/70">
                      <MdOutlineClose size={16} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <button
            className="w-full rounded-full bg-gradient-to-r from-emerald-400 to-green-500 px-4 py-3.5 text-[15px] font-bold text-[#04120c] shadow-[0_8px_24px_rgba(52,211,153,0.35)] transition active:scale-[0.99] disabled:opacity-50"
            disabled={sending}
          >
            {sending ? "Sending…" : "Send message"}
          </button>
        </form>
      </div>
    </main>
  );
}
