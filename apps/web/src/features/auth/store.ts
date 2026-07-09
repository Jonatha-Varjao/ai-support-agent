import { create } from "zustand";
import { me, type User } from "../../api/auth";

type AuthStatus = "idle" | "hydrating" | "ready";

interface AuthState {
  user: User | null;
  authStatus: AuthStatus;
  setUser: (u: User | null) => void;
  logout: () => void;
  hydrate: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  authStatus: "idle",

  setUser: (u) => set({ user: u, authStatus: "ready" }),

  logout: () => set({ user: null }),

  hydrate: async () => {
    if (useAuthStore.getState().authStatus !== "idle") return;
    set({ authStatus: "hydrating" });
    try {
      const user = await me();
      set({ user, authStatus: "ready" });
    } catch {
      set({ user: null, authStatus: "ready" });
    }
  },
}));
