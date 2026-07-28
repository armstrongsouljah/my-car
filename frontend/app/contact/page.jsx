"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { MdOutlineAttachFile, MdOutlineClose } from "react-icons/md";
import { api, getUser, isLoggedIn } from "@/lib/api";

const SUBJECTS = [
  ["general_account", "General Account"],
  ["app_inquiry", "App Inquiry"],
  ["feature_suggestion", "Feature Suggestions"],
  ["other", "Other"],
];

const MAX_ATTACHMENTS = 5;
const MAX_ATTACHMENT_SIZE_MB = 10;

function initialForm() {
  const user = getUser();
  return {
    name: [user?.first_name, user?.last_name].filter(Boolean).join(" ") || "",
    email: user?.email || "",
    subject: "general_account",
    custom_subject: "",
    message: "",
  };
}

export default function ContactPage() {
  const router = useRouter();
  const [form, setForm] = useState(initialForm);
  const [files, setFiles] = useState([]);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  function goBack() {
    if (typeof window !== "undefined" && window.history.length > 1) router.back();
    else router.push(isLoggedIn() ? "/settings" : "/");
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

  if (sent) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-3 px-6 text-center">
        <p className="text-3xl">✅</p>
        <h1 className="text-xl font-bold">Message sent</h1>
        <p className="max-w-xs text-sm text-gray-500 dark:text-gray-400">
          Thanks for reaching out — we&apos;ve got your message and will get back to you soon.
        </p>
        <Link href={isLoggedIn() ? "/settings" : "/"} className="mt-2 text-sm font-medium underline underline-offset-2">
          {isLoggedIn() ? "Back to Settings" : "Back home"}
        </Link>
      </main>
    );
  }

  return (
    <main className="space-y-4 px-4 pb-12 pt-6">
      <button onClick={goBack} className="mb-1 text-sm text-gray-500 dark:text-gray-400">‹ Back</button>

      <div>
        <h1 className="text-2xl font-bold">Contact support</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Trouble activating your account, a general question, or feedback on the app — tell us what&apos;s up and
          we&apos;ll reply by email.
        </p>
      </div>

      {error && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-400">{error}</p>}

      <form onSubmit={handleSubmit} className="card space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label" htmlFor="name">Name</label>
            <input id="name" className="input" required value={form.name} onChange={update("name")} />
          </div>
          <div>
            <label className="label" htmlFor="email">Email</label>
            <input id="email" className="input" type="email" required value={form.email} onChange={update("email")} />
          </div>
        </div>

        <div>
          <label className="label" htmlFor="subject">Subject</label>
          <select id="subject" className="input" value={form.subject} onChange={update("subject")}>
            {SUBJECTS.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        {form.subject === "other" && (
          <div>
            <label className="label" htmlFor="custom_subject">What&apos;s it about?</label>
            <input
              id="custom_subject"
              className="input"
              required
              placeholder="A short subject line"
              value={form.custom_subject}
              onChange={update("custom_subject")}
            />
          </div>
        )}

        <div>
          <label className="label" htmlFor="message">Message</label>
          <textarea
            id="message"
            className="input min-h-32 resize-y"
            required
            placeholder="Tell us what's going on…"
            value={form.message}
            onChange={update("message")}
          />
        </div>

        <div>
          <label className="label">Attachments (optional)</label>
          <label className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-gray-300 px-4 py-3 text-[13px] font-medium text-gray-500 dark:border-gray-700 dark:text-gray-400">
            <MdOutlineAttachFile size={17} />
            Add files (up to {MAX_ATTACHMENTS}, {MAX_ATTACHMENT_SIZE_MB}MB each)
            <input type="file" multiple className="hidden" onChange={addFiles} />
          </label>

          {files.length > 0 && (
            <ul className="mt-2 space-y-1.5">
              {files.map((file, index) => (
                <li key={`${file.name}-${index}`} className="flex items-center justify-between gap-2 rounded-lg bg-gray-50 px-3 py-2 text-[13px] dark:bg-gray-800">
                  <span className="truncate">{file.name}</span>
                  <button type="button" onClick={() => removeFile(index)} aria-label={`Remove ${file.name}`} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                    <MdOutlineClose size={16} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <button className="btn-primary" disabled={sending}>
          {sending ? "Sending…" : "Send message"}
        </button>
      </form>
    </main>
  );
}
