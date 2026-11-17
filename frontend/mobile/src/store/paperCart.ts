import Taro from "@tarojs/taro";
import { createStore } from "./createStore";

export type CartPaper = {
  id: string;
  title: string;
  authors?: string[];
  year?: number | null;
};

type PaperCartState = {
  items: CartPaper[];
  hydrate: () => void;
  add: (paper: CartPaper) => { ok: boolean; reason?: string };
  remove: (id: string) => void;
  clear: () => void;
  has: (id: string) => boolean;
};

const KEY = "paper-agent-cart";
const MAX_ITEMS = 8;

function read(): CartPaper[] {
  try {
    const raw = Taro.getStorageSync(KEY);
    if (!raw) return [];
    const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
    return Array.isArray(parsed?.items) ? parsed.items : Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function write(items: CartPaper[]) {
  Taro.setStorageSync(KEY, JSON.stringify({ items }));
}

export const usePaperCartStore = createStore<PaperCartState>((set, get) => ({
  items: [],
  hydrate: () => set({ items: read() }),
  add: (paper) => {
    const id = (paper.id || "").trim();
    if (!id) return { ok: false, reason: "缺少论文编码" };
    const cur = get().items;
    if (cur.some((x) => x.id === id)) return { ok: false, reason: "已在备选篮中" };
    if (cur.length >= MAX_ITEMS) return { ok: false, reason: `备选篮最多 ${MAX_ITEMS} 篇` };
    const next = [
      ...cur,
      {
        id,
        title: paper.title || id,
        authors: paper.authors || [],
        year: paper.year ?? null,
      },
    ];
    write(next);
    set({ items: next });
    return { ok: true };
  },
  remove: (id) => {
    const next = get().items.filter((x) => x.id !== id);
    write(next);
    set({ items: next });
  },
  clear: () => {
    write([]);
    set({ items: [] });
  },
  has: (id) => get().items.some((x) => x.id === id),
}));
