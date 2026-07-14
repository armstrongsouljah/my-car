"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, setTokens, setUser, isLoggedIn } from "@/lib/api";

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

export default function AuthPage() {
  const router = useRouter();
  const [mode, setMode] = useState("login"); // login | signup | verify
  const [form, setForm] = useState({ email: "", password: "", first_name: "", last_name: "", otp: "" });
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);
  const googleButtonRef = useRef(null);

  useEffect(() => {
    if (isLoggedIn()) router.replace("/dashboard");
  }, [router]);

  // ── Google Sign-In ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || mode === "verify") return;

    const init = () => {
      if (!window.google || !googleButtonRef.current) return;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (response) => {
          try {
            setLoading(true);
            const data = await api("/auth/google/", { method: "POST", body: { id_token: response.credential } });
            setTokens(data.tokens);
            setUser(data.user);
            router.replace("/dashboard");
          } catch (err) {
            setError(err.message);
          } finally {
            setLoading(false);
          }
        },
      });
      window.google.accounts.id.renderButton(googleButtonRef.current, {
        theme: "outline",
        size: "large",
        width: "100%",
        text: "continue_with",
      });
    };

    if (window.google) {
      init();
    } else {
      const script = document.createElement("script");
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.onload = init;
      document.body.appendChild(script);
    }
  }, [mode, router]);

  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setInfo("");
    setLoading(true);

    try {
      if (mode === "login") {
        const data = await api("/auth/login/", {
          method: "POST",
          body: { email: form.email, password: form.password },
        });
        setTokens(data.tokens);
        setUser(data.user);
        router.replace("/dashboard");
      } else if (mode === "signup") {
        await api("/auth/register/", {
          method: "POST",
          body: {
            email: form.email,
            password: form.password,
            first_name: form.first_name,
            last_name: form.last_name,
          },
        });
        setInfo(`We sent a 6-digit code to ${form.email}.`);
        setMode("verify");
      } else if (mode === "verify") {
        const data = await api("/auth/verify-email/", {
          method: "POST",
          body: { email: form.email, otp: form.otp },
        });
        setTokens(data.tokens);
        setUser(data.user);
        router.replace("/dashboard");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function resendOtp() {
    setError("");
    try {
      await api("/auth/resend-otp/", { method: "POST", body: { email: form.email } });
      setInfo(`A new code was sent to ${form.email}.`);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <main className="flex min-h-screen flex-col justify-center px-6 py-10">
      <div className="mb-8 text-center">
        <div className="text-4xl">🚗</div>
        <h1 className="mt-2 text-2xl font-bold">My Car</h1>
        <p className="mt-1 text-sm text-gray-500">Service history, reminders and expenses — all your cars in one place.</p>
      </div>

      {mode !== "verify" && (
        <div className="mb-6 grid grid-cols-2 rounded-xl bg-gray-200 p-1 text-sm font-semibold">
          <button
            className={`rounded-lg py-2 ${mode === "login" ? "bg-white shadow" : "text-gray-500"}`}
            onClick={() => setMode("login")}
          >
            Log in
          </button>
          <button
            className={`rounded-lg py-2 ${mode === "signup" ? "bg-white shadow" : "text-gray-500"}`}
            onClick={() => setMode("signup")}
          >
            Sign up
          </button>
        </div>
      )}

      {info && <p className="mb-4 rounded-xl bg-blue-50 p-3 text-sm text-blue-700">{info}</p>}
      {error && <p className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <form onSubmit={handleSubmit} className="space-y-4">
        {mode === "signup" && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">First name</label>
              <input className="input" value={form.first_name} onChange={update("first_name")} />
            </div>
            <div>
              <label className="label">Last name</label>
              <input className="input" value={form.last_name} onChange={update("last_name")} />
            </div>
          </div>
        )}

        {mode !== "verify" && (
          <>
            <div>
              <label className="label">Email</label>
              <input className="input" type="email" required autoComplete="email" value={form.email} onChange={update("email")} />
            </div>
            <div>
              <label className="label">Password</label>
              <input
                className="input"
                type="password"
                required
                minLength={8}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={form.password}
                onChange={update("password")}
              />
            </div>
          </>
        )}

        {mode === "verify" && (
          <div>
            <label className="label">Verification code</label>
            <input
              className="input text-center text-2xl tracking-[0.5em]"
              inputMode="numeric"
              maxLength={6}
              required
              value={form.otp}
              onChange={update("otp")}
            />
            <button type="button" onClick={resendOtp} className="mt-2 text-sm font-medium text-gray-500 underline">
              Resend code
            </button>
          </div>
        )}

        <button className="btn-primary" disabled={loading}>
          {loading ? "Please wait…" : mode === "login" ? "Log in" : mode === "signup" ? "Create account" : "Verify & continue"}
        </button>
      </form>

      {mode !== "verify" && GOOGLE_CLIENT_ID && (
        <>
          <div className="my-6 flex items-center gap-3 text-xs text-gray-400">
            <div className="h-px flex-1 bg-gray-200" /> OR <div className="h-px flex-1 bg-gray-200" />
          </div>
          <div ref={googleButtonRef} className="flex justify-center" />
        </>
      )}
    </main>
  );
}
