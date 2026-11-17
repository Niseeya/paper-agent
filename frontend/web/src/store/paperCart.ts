import { create } from "zustand";
import { persist } from "zustand/middleware";

export type CartPaper = {
  id: string;
  title: string;
  authors?: string[];
  year?: number | null;
};

type PaperCartState = {
  items: CartPaper[];
  add: (paper: CartPaper) => { ok: boolean; reason?: string };
  remove: (id: string) => void;
  clear: () => void;
  has: (id: string) => boolean;
};

const MAX_ITEMS = 8;

export const usePaperCartStore = create<PaperCartState>()(
  persist(
    (set, get) => ({
      items: [],
      add: (paper) => {
        const id = (paper.id || "").trim();
        if (!id) return { ok: false, reason: "缺少论文编码" };
        const cur = get().items;
        if (cur.some((x) => x.id === id)) return { ok: false, reason: "已在备选篮中" };
        if (cur.length >= MAX_ITEMS) return { ok: false, reason: `备选篮最多 ${MAX_ITEMS} 篇（对比上限）` };
        set({
          items: [
            ...cur,
            {
              id,
              title: paper.title || id,
              authors: paper.authors || [],
              year: paper.year ?? null,
            },
          ],
        });
        return { ok: true };
      },
      remove: (id) => set({ items: get().items.filter((x) => x.id !== id) }),
      clear: () => set({ items: [] }),
      has: (id) => get().items.some((x) => x.id === id),
    }),
    { name: "paper-agent-cart" }
  )
);
