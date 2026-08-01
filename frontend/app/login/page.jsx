"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Dancing_Script } from "next/font/google";
import { api, setTokens, setUser, isLoggedIn } from "@/lib/api";
import { COUNTRIES, flagEmoji } from "@/lib/countries";

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
const brandFont = Dancing_Script({ subsets: ["latin"], weight: ["700"] });

// Module-scoped (not component refs): GIS's initialize() resets its client
// config if called more than once per page per Google's own docs, and the
// <script> tag it needs shouldn't be appended twice either. Refs reset on
// every remount (e.g. logout -> back to /login), which would trigger both,
// so these need to survive across that remount instead.
let googleInitialized = false;
let googleScriptLoading = false;

// Reads fresh from window.location rather than the useSearchParams() hook's
// value so the long-lived Google Identity Services callback (initialized
// once per page load — see googleInitialized) can't close over a stale
// `next` from whatever query string was present at that first render.
function getNextPath() {
  if (typeof window === "undefined") return "/dashboard";
  const next = new URLSearchParams(window.location.search).get("next");
  // Must be an in-app path, never an absolute/protocol-relative URL —
  // otherwise a crafted `?next=` turns this into an open redirect.
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/dashboard";
}

function MailIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m3 7 9 6 9-6" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}

function EyeIcon({ open }) {
  return open ? (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ) : (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3l18 18" />
      <path d="M10.6 5.1A10.9 10.9 0 0 1 12 5c6.5 0 10 7 10 7a15.6 15.6 0 0 1-3.4 4.3M6.7 6.7C4 8.5 2 12 2 12s3.5 7 10 7a10.6 10.6 0 0 0 4.2-.9" />
      <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
    </svg>
  );
}

function AuthPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Landing page CTAs can link straight to the signup tab via ?mode=signup;
  // the verify-email reminder email links straight to ?mode=verify&email=...
  // so a stale/unverified signup can finish without typing the address again.
  // Anyone else (the hero's "Sign in" link, a bare /login visit) gets login.
  const initialMode = searchParams.get("mode");
  const [mode, setMode] = useState(
    initialMode === "signup" || initialMode === "verify" ? initialMode : "login"
  ); // login | signup | verify | forgot | reset
  const [form, setForm] = useState({
    email: searchParams.get("email") || "", password: "", first_name: "", last_name: "", otp: "",
    new_password: "", confirm_new_password: "", country: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);
  const googleButtonRef = useRef(null);

  useEffect(() => {
    if (isLoggedIn()) router.replace(getNextPath());
  }, [router]);

  // The useState initializers above only run once, on mount — if /login stays
  // mounted (e.g. a verify-email link is opened while another /login tab-nav
  // already has the app loaded) a changed ?mode=&email= wouldn't otherwise be
  // picked up, leaving a deep link stuck showing stale mode/email. searchParams
  // only changes identity on an actual URL change, not on our own setMode/
  // setForm calls below, so this can't clobber in-page transitions like
  // signup -> verify that never touch the URL.
  useEffect(() => {
    const urlMode = searchParams.get("mode");
    const urlEmail = searchParams.get("email");
    if (urlMode === "signup" || urlMode === "verify") setMode(urlMode);
    if (urlEmail) setForm((prev) => (prev.email === urlEmail ? prev : { ...prev, email: urlEmail }));
  }, [searchParams]);

  // ── Google Sign-In ──────────────────────────────────────────────────────────
  // GIS must only be initialize()d once per page (repeat calls reset its
  // global state) — the button itself does need re-rendering on mode change
  // since its container unmounts while mode === "verify".
  const showAccountSwitches = mode === "login" || mode === "signup";

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !showAccountSwitches) return;

    const renderButton = () => {
      if (!googleButtonRef.current) return;
      // GIS wants a pixel width (200–400), not a percentage — measure the container.
      const width = Math.min(400, Math.max(200, Math.round(googleButtonRef.current.offsetWidth)));
      window.google.accounts.id.renderButton(googleButtonRef.current, {
        theme: "filled_black",
        size: "large",
        width,
        text: "continue_with",
        shape: "pill",
      });
    };

    const initOnce = () => {
      if (googleInitialized) return;
      googleInitialized = true;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (response) => {
          try {
            setLoading(true);
            const data = await api("/auth/google/", { method: "POST", body: { id_token: response.credential } });
            setTokens(data.tokens);
            setUser(data.user);
            router.replace(getNextPath());
          } catch (err) {
            setError(err.message);
          } finally {
            setLoading(false);
          }
        },
      });
    };

    if (window.google) {
      initOnce();
      renderButton();
    } else if (!googleScriptLoading) {
      googleScriptLoading = true;
      const script = document.createElement("script");
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.onload = () => {
        initOnce();
        renderButton();
      };
      document.body.appendChild(script);
    }
  }, [mode, router]);

  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  // Backing out of an incomplete flow (verify/forgot/reset, or switching
  // between login/signup) shouldn't leave a half-typed password or an
  // abandoned OTP sitting in state to resurface in a later flow on the
  // same page load.
  function switchMode(nextMode) {
    setError("");
    setInfo("");
    setForm((prev) => ({
      ...prev, email: "", password: "", otp: "", new_password: "", confirm_new_password: "",
    }));
    setMode(nextMode);
  }

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
        router.replace(getNextPath());
      } else if (mode === "signup") {
        await api("/auth/register/", {
          method: "POST",
          body: {
            email: form.email,
            password: form.password,
            first_name: form.first_name,
            last_name: form.last_name,
            country: form.country,
          },
        });
        // The API returns the same response whether or not the address is
        // already registered, so the copy has to cover both: a new account
        // gets a code, an existing one gets a "you already have an account"
        // email and should sign in instead.
        setInfo(
          `We sent a 6-digit code to ${form.email}. Already have an account with that address? ` +
          `Sign in instead — we've emailed you a reminder.`
        );
        setMode("verify");
      } else if (mode === "verify") {
        const data = await api("/auth/verify-email/", {
          method: "POST",
          body: { email: form.email, otp: form.otp },
        });
        setTokens(data.tokens);
        setUser(data.user);
        router.replace(getNextPath());
      } else if (mode === "forgot") {
        await api("/auth/password/reset/request/", {
          method: "POST",
          body: { email: form.email },
        });
        // Same response whether or not the address has an account — the copy
        // has to stay generic either way.
        setInfo(`If ${form.email} has an account, we've sent a 6-digit reset code to it.`);
        setMode("reset");
      } else if (mode === "reset") {
        const data = await api("/auth/password/reset/confirm/", {
          method: "POST",
          body: {
            email: form.email,
            otp: form.otp,
            new_password: form.new_password,
            confirm_new_password: form.confirm_new_password,
          },
        });
        setTokens(data.tokens);
        setUser(data.user);
        router.replace(getNextPath());
      }
    } catch (err) {
      if (mode === "login" && err.status === 403 && /verify your email/i.test(err.message)) {
        try {
          await api("/auth/resend-otp/", { method: "POST", body: { email: form.email } });
          setInfo("A new code has been sent to your email. Didn't get it after 2 minutes? Hit \"Resend code\" below.");
        } catch {
          setInfo(`Enter the code we sent to ${form.email}, or resend one below.`);
        }
        setMode("verify");
      } else {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }

  async function resendOtp() {
    setError("");
    try {
      const path = mode === "reset" ? "/auth/password/reset/request/" : "/auth/resend-otp/";
      await api(path, { method: "POST", body: { email: form.email } });
      setInfo(`A new code was sent to ${form.email}.`);
    } catch (err) {
      setError(err.message);
    }
  }

  const tagline =
    mode === "signup" ? "Your garage starts here"
    : mode === "verify" || mode === "reset" ? "Check your inbox for the code"
    : mode === "forgot" ? "Let's get you back in"
    : "Welcome back to your garage";

  return (
    <main className="flex min-h-screen flex-col bg-[#04120c] text-white">
      {/* Hero */}
      <div className="relative h-80 overflow-hidden">
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
          <h1
            className={`${brandFont.className} text-4xl font-bold tracking-wide text-white drop-shadow-[0_2px_10px_rgba(0,0,0,0.9)]`}
          >
            GlavBox
          </h1>
          <p className="mt-0.5 text-sm text-emerald-100/80 drop-shadow-[0_1px_6px_rgba(0,0,0,0.9)]">{tagline}</p>
        </div>
      </div>

      {/* Form sheet */}
      <div className="relative flex-1 rounded-t-[32px] bg-[#0a1a14] px-6 pb-10 pt-8 shadow-[0_-20px_60px_rgba(0,0,0,0.5)]">
        {showAccountSwitches && (
          <div className="mb-6 grid grid-cols-2 rounded-full bg-white/5 p-1 text-sm font-semibold">
            <button
              type="button"
              className={`rounded-full py-2.5 transition ${mode === "login" ? "bg-emerald-400 text-[#04120c]" : "text-white/50"}`}
              onClick={() => setMode("login")}
            >
              Log in
            </button>
            <button
              type="button"
              className={`rounded-full py-2.5 transition ${mode === "signup" ? "bg-emerald-400 text-[#04120c]" : "text-white/50"}`}
              onClick={() => setMode("signup")}
            >
              Sign up
            </button>
          </div>
        )}

        {info && <p className="mb-4 rounded-xl bg-emerald-400/10 p-3 text-sm text-emerald-300">{info}</p>}
        {error && <p className="mb-4 rounded-xl bg-red-400/10 p-3 text-sm text-red-300">{error}</p>}

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "signup" && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="auth-label" htmlFor="first_name">First name</label>
                <input id="first_name" className="auth-input" value={form.first_name} onChange={update("first_name")} />
              </div>
              <div>
                <label className="auth-label" htmlFor="last_name">Last name</label>
                <input id="last_name" className="auth-input" value={form.last_name} onChange={update("last_name")} />
              </div>
            </div>
          )}

          {mode === "signup" && (
            <div>
              <label className="auth-label" htmlFor="country">Country</label>
              <select id="country" className="auth-input" value={form.country} onChange={update("country")}>
                <option value="">Prefer not to say</option>
                {COUNTRIES.map(([code, name]) => (
                  <option key={code} value={code}>{flagEmoji(code)} {name}</option>
                ))}
              </select>
              <p className="mt-1 text-[12px] text-white/40">
                Sets your default currency for expenses and reports — you can change it later in Settings.
              </p>
            </div>
          )}

          {(mode === "login" || mode === "signup" || mode === "forgot") && (
            <div>
              <label className="auth-label" htmlFor="email">Email address</label>
              <div className="relative">
                <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-white/40">
                  <MailIcon />
                </span>
                <input
                  id="email"
                  className="auth-input pl-11"
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={update("email")}
                />
              </div>
            </div>
          )}

          {(mode === "login" || mode === "signup") && (
            <div>
              <label className="auth-label" htmlFor="password">Password</label>
              <div className="relative">
                <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-white/40">
                  <LockIcon />
                </span>
                <input
                  id="password"
                  className="auth-input pl-11 pr-11"
                  type={showPassword ? "text" : "password"}
                  required
                  minLength={8}
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  placeholder="Enter password"
                  value={form.password}
                  onChange={update("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/70"
                >
                  <EyeIcon open={showPassword} />
                </button>
              </div>
              {mode === "login" && (
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => { setError(""); setInfo(""); setMode("forgot"); }}
                  className="mt-2 text-sm font-medium text-emerald-400 underline underline-offset-2 disabled:opacity-50"
                >
                  Forgot password?
                </button>
              )}
            </div>
          )}

          {(mode === "verify" || mode === "reset") && (
            <div>
              <label className="auth-label" htmlFor="otp">Verification code</label>
              <input
                id="otp"
                className="auth-input text-center text-2xl tracking-[0.5em]"
                inputMode="numeric"
                maxLength={6}
                required
                value={form.otp}
                onChange={update("otp")}
              />
              <button type="button" onClick={resendOtp} className="mt-2 text-sm font-medium text-emerald-400 underline underline-offset-2">
                Resend code
              </button>
            </div>
          )}

          {mode === "reset" && (
            <>
              <div>
                <label className="auth-label" htmlFor="new_password">New password</label>
                <div className="relative">
                  <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-white/40">
                    <LockIcon />
                  </span>
                  <input
                    id="new_password"
                    className="auth-input pl-11 pr-11"
                    type={showPassword ? "text" : "password"}
                    required
                    minLength={8}
                    autoComplete="new-password"
                    placeholder="Enter new password"
                    value={form.new_password}
                    onChange={update("new_password")}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/70"
                  >
                    <EyeIcon open={showPassword} />
                  </button>
                </div>
              </div>
              <div>
                <label className="auth-label" htmlFor="confirm_new_password">Confirm new password</label>
                <input
                  id="confirm_new_password"
                  className="auth-input"
                  type={showPassword ? "text" : "password"}
                  required
                  minLength={8}
                  autoComplete="new-password"
                  placeholder="Re-enter new password"
                  value={form.confirm_new_password}
                  onChange={update("confirm_new_password")}
                />
              </div>
            </>
          )}

          <button
            className="w-full rounded-full bg-gradient-to-r from-emerald-400 to-green-500 px-4 py-3.5 text-[15px] font-bold text-[#04120c] shadow-[0_8px_24px_rgba(52,211,153,0.35)] transition active:scale-[0.99] disabled:opacity-50"
            disabled={loading}
          >
            {loading ? "Please wait…"
              : mode === "login" ? "Sign in"
              : mode === "signup" ? "Sign up"
              : mode === "forgot" ? "Send reset code"
              : mode === "reset" ? "Reset password"
              : "Verify & continue"}
          </button>
        </form>

        {showAccountSwitches && GOOGLE_CLIENT_ID && (
          <>
            <div className="my-6 flex items-center gap-3 text-xs text-white/30">
              <div className="h-px flex-1 bg-white/10" /> or continue with <div className="h-px flex-1 bg-white/10" />
            </div>
            <div ref={googleButtonRef} className="flex justify-center" />
          </>
        )}

        {showAccountSwitches && (
          <p className="mt-6 text-center text-sm text-white/50">
            {mode === "login" ? "Don't have an account? " : "Already have an account? "}
            <button
              type="button"
              disabled={loading}
              onClick={() => switchMode(mode === "login" ? "signup" : "login")}
              className="font-semibold text-emerald-400 disabled:opacity-50"
            >
              {mode === "login" ? "Sign up" : "Sign in"}
            </button>
          </p>
        )}

        {(mode === "verify" || mode === "forgot" || mode === "reset") && (
          <p className="mt-6 text-center text-sm text-white/50">
            <button
              type="button"
              disabled={loading}
              onClick={() => switchMode("login")}
              className="font-semibold text-emerald-400 disabled:opacity-50"
            >
              Back to log in
            </button>
          </p>
        )}

        <p className="mt-4 text-center text-sm text-white/40">
          Trouble signing in?{" "}
          <Link href="/contact" className="font-semibold text-emerald-400">
            Contact support
          </Link>
        </p>
      </div>
    </main>
  );
}

export default function Page() {
  return (
    <Suspense fallback={null}>
      <AuthPage />
    </Suspense>
  );
}
