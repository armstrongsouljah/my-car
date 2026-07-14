"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getTokens, clearSession, setUser } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import BottomNav from "@/components/BottomNav";

function Section({ title, children }) {
  return (
    <section className="card space-y-3">
      <p className="font-semibold">{title}</p>
      {children}
    </section>
  );
}

function Settings() {
  const router = useRouter();
  const [profile, setProfile] = useState(null);
  const [profileForm, setProfileForm] = useState({ first_name: "", last_name: "", phone: "" });
  const [passwordForm, setPasswordForm] = useState({ current_password: "", new_password: "", confirm_new_password: "" });
  const [deactivatePassword, setDeactivatePassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api("/auth/profile/")
      .then((data) => {
        setProfile(data);
        setProfileForm({ first_name: data.first_name || "", last_name: data.last_name || "", phone: data.phone || "" });
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

  async function deactivate(event) {
    event.preventDefault();
    if (!confirm("Deactivate your account? You will be signed out and unable to log back in.")) return;
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
    }
  }

  return (
    <main className="space-y-4 px-4 pb-24 pt-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {message && <p className="rounded-xl bg-green-50 p-3 text-sm text-green-700">{message}</p>}
      {error && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <Section title="Account details">
        {profile && <p className="text-sm text-gray-500">{profile.email}</p>}
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

      <Section title="Danger zone">
        <p className="text-sm text-gray-500">
          Deactivating your account signs you out everywhere and disables logins. Your data is kept and support can reactivate you.
        </p>
        <form onSubmit={deactivate} className="space-y-3">
          <div>
            <label className="label">Confirm with your password</label>
            <input className="input" type="password" value={deactivatePassword}
              onChange={(e) => setDeactivatePassword(e.target.value)} />
          </div>
          <button className="w-full rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-[15px] font-semibold text-red-600">
            Deactivate account
          </button>
        </form>
      </Section>

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
