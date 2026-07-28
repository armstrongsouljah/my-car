"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, getTokens, clearSession, setUser } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";
import ConfirmDialog from "@/components/ConfirmDialog";
import Spinner from "@/components/Spinner";
import { useTheme } from "@/components/ThemeProvider";

const REMINDER_FREQUENCIES = [
  ["off", "Off"],
  ["daily", "Daily"],
  ["weekly", "Weekly"],
  ["monthly", "Monthly"],
];
const REMINDER_LABELS = Object.fromEntries(REMINDER_FREQUENCIES);

const THEME_OPTIONS = [
  ["light", "Light", "☀️"],
  ["dark", "Dark", "🌙"],
  ["system", "System", "🖥️"],
];

function Section({ title, action, children }) {
  return (
    <section className="card space-y-3">
      <div className="flex items-center justify-between">
        <p className="font-semibold">{title}</p>
        {action}
      </div>
      {children}
    </section>
  );
}

function AppearanceSection() {
  const { theme, setTheme } = useTheme();
  return (
    <Section title="Appearance">
      <div className="flex rounded-full bg-gray-100 p-1 dark:bg-gray-800">
        {THEME_OPTIONS.map(([value, label, icon]) => (
          <button
            key={value}
            type="button"
            onClick={() => setTheme(value)}
            aria-pressed={theme === value}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-full py-2 text-[13px] font-medium transition ${
              theme === value
                ? "bg-gray-900 text-white dark:bg-white dark:text-gray-900"
                : "text-gray-500 dark:text-gray-400"
            }`}
          >
            <span>{icon}</span>
            {label}
          </button>
        ))}
      </div>
    </Section>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5 text-sm">
      <span className="text-gray-500 dark:text-gray-400">{label}</span>
      <span className="truncate font-medium">{value}</span>
    </div>
  );
}

function ToggleRow({ label, danger, open, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-expanded={open}
      className={`flex w-full items-center justify-between py-2 text-[15px] font-medium ${
        danger ? "text-red-600 dark:text-red-400" : ""
      }`}
    >
      {label}
      <span className={`text-gray-300 transition-transform dark:text-gray-600 ${open ? "rotate-90" : ""}`}>›</span>
    </button>
  );
}

const emptyProfileForm = { first_name: "", last_name: "", phone: "", mileage_reminder_frequency: "off" };
const emptyPasswordForm = { current_password: "", new_password: "", confirm_new_password: "" };

function profileFormFrom(data) {
  return {
    first_name: data.first_name || "",
    last_name: data.last_name || "",
    phone: data.phone || "",
    mileage_reminder_frequency: data.mileage_reminder_frequency || "off",
  };
}

function Settings() {
  const router = useRouter();
  const [profile, setProfile] = useState(null);
  const [profileForm, setProfileForm] = useState(emptyProfileForm);
  const [editingProfile, setEditingProfile] = useState(false);

  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [passwordForm, setPasswordForm] = useState(emptyPasswordForm);

  const [showDeactivate, setShowDeactivate] = useState(false);
  const [confirmDeactivate, setConfirmDeactivate] = useState(false);
  const [deactivating, setDeactivating] = useState(false);
  const [deactivatePassword, setDeactivatePassword] = useState("");

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api("/auth/profile/")
      .then((data) => {
        setProfile(data);
        setProfileForm(profileFormFrom(data));
      })
      .catch((err) => setError(err.message));
  }, []);

  function flash(text) {
    setError("");
    setMessage(text);
    setTimeout(() => setMessage(""), 4000);
  }

  function startEditingProfile() {
    setEditingProfile(true);
  }

  function cancelEditingProfile() {
    if (profile) setProfileForm(profileFormFrom(profile));
    setEditingProfile(false);
  }

  const isProfileDirty =
    !!profile &&
    JSON.stringify(profileForm) !== JSON.stringify(profileFormFrom(profile));

  async function saveProfile(event) {
    event.preventDefault();
    try {
      const data = await api("/auth/profile/", { method: "PATCH", body: profileForm });
      setProfile(data);
      setUser(data);
      setEditingProfile(false);
      flash("Profile updated.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function changePassword(event) {
    event.preventDefault();
    try {
      await api("/auth/password/change/", { method: "POST", body: passwordForm });
      setPasswordForm(emptyPasswordForm);
      setShowPasswordForm(false);
      flash("Password updated.");
    } catch (err) {
      setError(err.message);
    }
  }

  function cancelPasswordForm() {
    setPasswordForm(emptyPasswordForm);
    setShowPasswordForm(false);
  }

  async function logout() {
    const tokens = getTokens();
    try {
      if (tokens?.refresh) await api("/auth/logout/", { method: "POST", body: { refresh: tokens.refresh } });
    } catch {
      // best effort
    }
    clearSession();
    router.replace("/login");
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
      router.replace("/login");
    } catch (err) {
      setError(err.message);
      setDeactivating(false);
      setConfirmDeactivate(false);
    }
  }

  const fullName = [profile?.first_name, profile?.last_name].filter(Boolean).join(" ");

  return (
    <main className="space-y-4 px-4 pb-24 pt-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Settings</h1>
        <button
          onClick={logout}
          className="rounded-full border border-gray-200 px-3 py-1.5 text-[13px] font-medium text-gray-600 transition active:scale-95 dark:border-gray-700 dark:text-gray-300"
        >
          Log out
        </button>
      </div>

      {message && <p className="rounded-xl bg-green-50 p-3 text-sm text-green-700 dark:bg-green-500/10 dark:text-green-400">{message}</p>}
      {error && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-400">{error}</p>}

      <AppearanceSection />

      <Section
        title="Account details"
        action={
          !editingProfile && profile && (
            <button type="button" onClick={startEditingProfile} className="text-sm font-medium underline underline-offset-2">
              Edit
            </button>
          )
        }
      >
        {!profile ? (
          <div className="flex justify-center py-2"><Spinner /></div>
        ) : !editingProfile ? (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            <InfoRow label="Email" value={profile.email} />
            <InfoRow label="Name" value={fullName || "—"} />
            <InfoRow label="Phone" value={profile.phone || "—"} />
            <InfoRow label="Mileage reminder" value={REMINDER_LABELS[profile.mileage_reminder_frequency] || "Off"} />
          </div>
        ) : (
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
            <div className="flex gap-2">
              {isProfileDirty && <button className="btn-primary">Save changes</button>}
              <button type="button" onClick={cancelEditingProfile} className="btn-secondary">Cancel</button>
            </div>
          </form>
        )}
      </Section>

      <Section title="Security">
        <ToggleRow label="Change password" open={showPasswordForm} onClick={() => setShowPasswordForm((v) => !v)} />
        {showPasswordForm && (
          <form onSubmit={changePassword} className="space-y-3 pb-1 pt-1">
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
            <div className="flex gap-2">
              <button className="btn-primary">Update password</button>
              <button type="button" onClick={cancelPasswordForm} className="btn-secondary">Cancel</button>
            </div>
          </form>
        )}

        <hr className="border-gray-100 dark:border-gray-800" />

        <ToggleRow
          label="Deactivate account"
          danger
          open={showDeactivate}
          onClick={() => setShowDeactivate((v) => !v)}
        />
        {showDeactivate && (
          <div className="space-y-3 pb-1 pt-1">
            {/* "30 days" mirrors Constants.ACCOUNT_DELETION_GRACE_DAYS (api/utils/Constants.py) —
                keep in sync with that value and the ConfirmDialog message below. */}
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Deactivating your account signs you out everywhere and disables logins right away. Your data is kept for
              30 days in case you change your mind — support can reactivate you within that window. After 30 days it&apos;s
              permanently deleted.
            </p>
            <div>
              <label className="label">Confirm with your password</label>
              <input className="input" type="password" value={deactivatePassword}
                onChange={(e) => setDeactivatePassword(e.target.value)} />
            </div>
            <button
              type="button"
              disabled={!deactivatePassword}
              onClick={() => setConfirmDeactivate(true)}
              className="w-full rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-[15px] font-semibold text-red-600 disabled:opacity-50 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400"
            >
              Deactivate account
            </button>
          </div>
        )}
      </Section>

      <Section title="Support">
        <Link href="/contact" className="flex w-full items-center justify-between py-2 text-[15px] font-medium">
          Contact support
          <span className="text-gray-300 dark:text-gray-600">›</span>
        </Link>
      </Section>

      <ConfirmDialog
        open={confirmDeactivate}
        destructive
        loading={deactivating}
        title="Deactivate your account?"
        message="You'll be signed out everywhere and won't be able to log back in. Your data is kept for 30 days in case you change your mind — after that it's permanently deleted."
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
