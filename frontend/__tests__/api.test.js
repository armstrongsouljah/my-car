import { setTokens, getTokens, clearSession, isLoggedIn } from "@/lib/api";

describe("session storage", () => {
  beforeEach(() => localStorage.clear());

  it("stores and reads tokens", () => {
    setTokens({ access: "a", refresh: "r" });
    expect(getTokens()).toEqual({ access: "a", refresh: "r" });
    expect(isLoggedIn()).toBe(true);
  });

  it("clears the session", () => {
    setTokens({ access: "a", refresh: "r" });
    clearSession();
    expect(getTokens()).toBeNull();
    expect(isLoggedIn()).toBe(false);
  });
});
