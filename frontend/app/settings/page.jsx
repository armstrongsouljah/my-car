"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, getTokens, clearSession, setUser } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import ConfirmDialog from "@/components/ConfirmDialog";
import { useTheme } from "@/components/ThemeProvider";

const REMINDER_FREQUENCIES = [
  ["off", "Off"],
  ["daily", "Daily"],
  ["weekly", "Weekly"],
  ["monthly", "Monthly"],
];

const THEME_OPTIONS = [
  ["light", "Light", "☀️"],
  ["dark", "Dark", "🌙"],
  ["system", "System", "🖥️"],
];

function Section({ title, children }) {
  return (
    <section className="card space-y-3">
      <p className="font-semibold">{title}</p>
      {children}
    </section>
  );
}

function AppearanceSection() {
  const { theme, setTheme } = useTheme();
  return (
    <Section title="Appearance">
      <div className="grid grid-cols-3 gap-2">
        {THEME_OPTIONS.map(([value, label, icon]) => (
          <button
            key={value}
            type="button"
            onClick={() => setTheme(value)}
            aria-pressed={theme === value}
            className={`flex flex-col items-center gap-1 rounded-xl border py-3 text-[13px] font-medium transition ${
              theme === value
                ? "border-gray-900 bg-gray-900 text-white dark:border-white dark:bg-white dark:text-gray-900"
                : "border-gray-200 text-gray-600 dark:border-gray-700 dark:text-gray-400"
            }`}
          >
            <span className="text-lg">{icon}</span>
            {label}
          </button>
        ))}
      </div>
    </Section>
  );
}

function Settings() {
  const router = useRouter();
  const [profile, setProfile] = useState(null);
  const [profileForm, setProfileForm] = useState({
    first_name: "", last_name: "", phone: "", mileage_reminder_frequency: "off",
  });
  const [confirmDeactivate, setConfirmDeactivate] = useState(false);
  const [deactivating, setDeactivating] = useState(false);
  const [passwordForm, setPasswordForm] = useState({ current_password: "", new_password: "", confirm_new_password: "" });
  const [deactivatePassword, setDeactivatePassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api("/auth/profile/")
      .then((data) => {
        setProfile(data);
        setProfileForm({
          first_name: data.first_name || "",
          last_name: data.last_name || "",
          phone: data.phone || "",
          mileage_reminder_frequency: data.mileage_reminder_frequency || "off",
        });
      })
      .catch((err) => setError(err.message));
  }, []);

  function flash(text) {
    setError("");
    setMessage(text);
    setTimeout(() => setMessage(""), 4000);
  }

  async function saveProfile(event) {
    event.preventDefault();
    try {
      const data = await api("/auth/profile/", { method: "PATCH", body: profileForm });
      setProfile(data);
      setUser(data);
      flash("Profile updated.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function changePassword(event) {
    event.preventDefault();
    try {
      await api("/auth/password/change/", { method: "POST", body: passwordForm });
      setPasswordForm({ current_password: "", new_password: "", confirm_new_password: "" });
      flash("Password updated.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function logout() {
    const tokens = getTokens();
    try {
      if (tokens?.refresh) await api("/auth/logout/", { method: "POST", body: { refresh: tokens.refresh } });
    } catch {
      // best effort
    }
    clearSession();
    router.replace("/");
  }

  async function deactivate() {
    setDeactivating(true);
    try {
      const tokens = getTokens();
      await api("/auth/account/deactivate/", {
        method: "POST",
        body: { password: deactivatePassword, refresh: tokens?.refresh },
      });
      clearSession();
      router.replace("/");
    } catch (err) {
      setError(err.message);
      setDeactivating(false);
      setConfirmDeactivate(false);
    }
  }

  return (
    <main className="space-y-4 px-4 pb-24 pt-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {message && <p className="rounded-xl bg-green-50 p-3 text-sm text-green-700 dark:bg-green-500/10 dark:text-green-400">{message}</p>}
      {error && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-400">{error}</p>}

      <AppearanceSection />

      <Section title="Account details">
        {profile && <p className="text-sm text-gray-500 dark:text-gray-400">{profile.email}</p>}
        <form onSubmit={saveProfile} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">First name</label>
              <input className="input" value={profileForm.first_name}
                onChange={(e) => setProfileForm({ ...profileForm, first_name: e.target.value })} />
            </div>
            <div>
              <label className="label">Last name</label>
              <input className="input" value={profileForm.last_name}
                onChange={(e) => setProfileForm({ ...profileForm, last_name: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="label">Phone</label>
            <input className="input" value={profileForm.phone}
              onChange={(e) => setProfileForm({ ...profileForm, phone: e.target.value })} />
          </div>
          <div>
            <label className="label">Mileage update reminder</label>
            <select
              className="input"
              value={profileForm.mileage_reminder_frequency}
              onChange={(e) => setProfileForm({ ...profileForm, mileage_reminder_frequency: e.target.value })}
            >
              {REMINDER_FREQUENCIES.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            <p className="mt-1 text-[12px] text-gray-400 dark:text-gray-500">
              We&apos;ll email you a nudge to update your cars&apos; odometer readings so service reminders stay accurate.
            </p>
          </div>
          <button className="btn-primary">Save changes</button>
        </form>
      </Section>

      <Section title="Change password">
        <form onSubmit={changePassword} className="space-y-3">
          <div>
            <label className="label">Current password</label>
            <input className="input" type="password" required value={passwordForm.current_password}
              onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })} />
          </div>
          <div>
            <label className="label">New password</label>
            <input className="input" type="password" required minLength={8} value={passwordForm.new_password}
              onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })} />
          </div>
          <div>
            <label className="label">Confirm new password</label>
            <input className="input" type="password" required value={passwordForm.confirm_new_password}
              onChange={(e) => setPasswordForm({ ...passwordForm, confirm_new_password: e.target.value })} />
          </div>
          <button className="btn-primary">Update password</button>
        </form>
      </Section>

      <Section title="Session">
        <button onClick={logout} className="btn-secondary">Log out</button>
      </Section>

      <Section title="Legal">
        <Link href="/about" className="block text-sm font-medium underline underline-offset-2">
          About GlavBox
        </Link>
        <Link href="/privacy" className="block text-sm font-medium underline underline-offset-2">
          Privacy &amp; Security
        </Link>
      </Section>

      <Section title="Danger zone">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Deactivating your account signs you out everywhere and disables logins right away. Your data is kept for
          60 days in case you change your mind — support can reactivate you within that window. After 60 days it&apos;s
          permanently deleted.
        </p>
        <div className="space-y-3">
          <div>
            <label className="label">Confirm with your password</label>
            <input className="input" type="password" value={deactivatePassword}
              onChange={(e) => setDeactivatePassword(e.target.value)} />
          </div>
          <button
            onClick={() => setConfirmDeactivate(true)}
            className="w-full rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-[15px] font-semibold text-red-600 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400"
          >
            Deactivate account
          </button>
        </div>
      </Section>

      <ConfirmDialog
        open={confirmDeactivate}
        destructive
        loading={deactivating}
        title="Deactivate your account?"
        message="You'll be signed out everywhere and won't be able to log back in. Your data is kept for 60 days in case you change your mind — after that it's permanently deleted."
        confirmLabel="Deactivate"
        cancelLabel="Keep my account"
        onConfirm={deactivate}
        onCancel={() => setConfirmDeactivate(false)}
      />

      <BottomNav />
    </main>
  );
}

export default function Page() {
  return (
    <AuthGuard>
      <Settings />
    </AuthGuard>
  );
}
