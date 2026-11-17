import Taro from "@tarojs/taro";
import { createStore } from "./createStore";

export type User = {
  id: string;
  username: string;
  display_name: string;
  role: string;
};

type AuthState = {
  token: string | null;
  user: User | null;
  hydrated: boolean;
  hydrate: () => void;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
};

const KEY = "paper-agent-auth";

function readStorage(): { token: string | null; user: User | null } {
  try {
    const raw = Taro.getStorageSync(KEY);
    if (!raw) return { token: null, user: null };
    const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
    return { token: parsed?.token || null, user: parsed?.user || null };
  } catch {
    return { token: null, user: null };
  }
}

function writeStorage(token: string | null, user: User | null) {
  if (!token) {
    Taro.removeStorageSync(KEY);
    return;
  }
  Taro.setStorageSync(KEY, JSON.stringify({ token, user }));
}

export const useAuthStore = createStore<AuthState>((set) => ({
  token: null,
  user: null,
  hydrated: false,
  hydrate: () => {
    const { token, user } = readStorage();
    set({ token, user, hydrated: true });
  },
  setAuth: (token, user) => {
    writeStorage(token, user);
    set({ token, user, hydrated: true });
  },
  logout: () => {
    writeStorage(null, null);
    set({ token: null, user: null, hydrated: true });
  },
}));
