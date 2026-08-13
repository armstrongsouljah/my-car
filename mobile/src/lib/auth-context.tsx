import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { GoogleSignin, isSuccessResponse } from '@react-native-google-signin/google-signin';

import { api, clearSession, getTokens, getUser, setTokens, setUser, SessionExpiredError, type Tokens } from '@/lib/api';

type User = { id: string; email: string; [key: string]: unknown };

type AuthContextValue = {
  // undefined: still loading the stored session on boot (see AuthGuard,
  // which mirrors frontend/components/AuthGuard.jsx's `ready` flag but has
  // to account for SecureStore's async read instead of sync localStorage).
  user: User | null | undefined;
  isLoggedIn: boolean;
  login: (email: string, password: string) => Promise<void>;
  // Same /auth/google/ endpoint as frontend/app/login/page.jsx's Google
  // Identity Services button -- webClientId (see GoogleSignin.configure
  // below) makes the native idToken's `aud` match what that endpoint
  // already verifies against, so no backend changes were needed for this.
  loginWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  // Wraps api() so a SessionExpiredError (refresh failed) clears local
  // state immediately instead of every screen needing its own try/catch
  // for that one case — screens still handle their own other errors.
  apiCall: typeof api;
};

// Configuring once at module scope (not per sign-in attempt) matches the
// library's docs -- it's a one-time native-SDK setup call, not per-request state.
GoogleSignin.configure({ webClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID });

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null | undefined>(undefined);

  useEffect(() => {
    (async () => {
      const [tokens, storedUser] = await Promise.all([getTokens(), getUser<User>()]);
      setUserState(tokens?.access ? storedUser : null);
    })();
  }, []);

  async function login(email: string, password: string) {
    const data = await api('/auth/login/', { method: 'POST', body: { email, password } });
    await setTokens(data.tokens as Tokens);
    await setUser(data.user);
    setUserState(data.user);
  }

  async function loginWithGoogle() {
    await GoogleSignin.hasPlayServices();
    const response = await GoogleSignin.signIn();
    if (!isSuccessResponse(response)) return; // user cancelled -- nothing to report as an error

    const data = await api('/auth/google/', { method: 'POST', body: { id_token: response.data.idToken } });
    await setTokens(data.tokens as Tokens);
    await setUser(data.user);
    setUserState(data.user);
  }

  async function logout() {
    await clearSession();
    setUserState(null);
  }

  async function apiCall(...args: Parameters<typeof api>) {
    try {
      return await api(...args);
    } catch (err) {
      if (err instanceof SessionExpiredError) {
        await clearSession();
        setUserState(null);
      }
      throw err;
    }
  }

  return (
    <AuthContext.Provider value={{ user, isLoggedIn: !!user, login, loginWithGoogle, logout, apiCall }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
