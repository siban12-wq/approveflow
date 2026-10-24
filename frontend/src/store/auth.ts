import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api, AuthUser, clearTokens, DEMO_PASSWORD, setTokens } from "@/lib/api";

type AuthState = {
  user: AuthUser | null;
  setUser: (user: AuthUser | null) => void;
  login: (email: string, password: string) => Promise<AuthUser>;
  logout: () => void;
};

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      setUser: (user) => set({ user }),
      login: async (email, password) => {
        const data = await api.post<{ access_token: string; refresh_token: string; user: AuthUser }>("/api/v1/auth/login", {
          email,
          password,
        });
        setTokens(data.access_token, data.refresh_token);
        set({ user: data.user });
        return data.user;
      },
      logout: () => {
        clearTokens();
        set({ user: null });
      },
    }),
    { name: "af-auth", partialize: (s) => ({ user: s.user }) },
  ),
);

export async function loginAsDemo(email: string) {
  return useAuth.getState().login(email, DEMO_PASSWORD);
}
