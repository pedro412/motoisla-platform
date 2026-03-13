"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { CartLine, ProductSearchItem } from "@/lib/types/sales";

interface CartState {
  lines: CartLine[];
  customerPhone: string;
  customerName: string;

  addOrIncrement: (product: ProductSearchItem) => boolean;
  updateLine: (index: number, patch: Partial<CartLine>) => void;
  setLineQty: (index: number, qty: number) => void;
  removeLine: (productId: string) => void;
  setCustomerPhone: (phone: string) => void;
  setCustomerName: (name: string) => void;
  clearCart: () => void;
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      lines: [],
      customerPhone: "",
      customerName: "",

      addOrIncrement: (product) => {
        const { lines } = get();
        const productStock = Number(product.stock);
        if (productStock <= 0) return false;

        const existingIndex = lines.findIndex((l) => l.product.id === product.id);
        if (existingIndex === -1) {
          set({
            lines: [
              ...lines,
              {
                product,
                qty: 1,
                unitPrice: Number(product.default_price),
                unitCost: Number(product.default_price) * 0.6,
                discountPct: 0,
              },
            ],
          });
          return true;
        }

        const existing = lines[existingIndex];
        if (existing.qty >= productStock) return false;

        set({
          lines: lines.map((line, i) =>
            i === existingIndex ? { ...line, qty: line.qty + 1 } : line,
          ),
        });
        return true;
      },

      updateLine: (index, patch) => {
        set((state) => ({
          lines: state.lines.map((line, i) => (i === index ? { ...line, ...patch } : line)),
        }));
      },

      setLineQty: (index, nextQty) => {
        const { lines } = get();
        const target = lines[index];
        if (!target) return;

        const maxQty = Math.max(0, Number(target.product.stock));
        const sanitized = Number.isFinite(nextQty) ? nextQty : 0;
        const clamped = Math.min(Math.max(0, sanitized), maxQty);

        if (clamped <= 0) {
          set({ lines: lines.filter((_, i) => i !== index) });
          return;
        }

        set({
          lines: lines.map((line, i) => (i === index ? { ...line, qty: clamped } : line)),
        });
      },

      removeLine: (productId) => {
        set((state) => ({
          lines: state.lines.filter((line) => line.product.id !== productId),
        }));
      },

      setCustomerPhone: (customerPhone) => set({ customerPhone }),
      setCustomerName: (customerName) => set({ customerName }),

      clearCart: () =>
        set({
          lines: [],
          customerPhone: "",
          customerName: "",
        }),
    }),
    {
      name: "motoisla-pos-cart",
      partialize: (state) => ({
        lines: state.lines,
        customerPhone: state.customerPhone,
        customerName: state.customerName,
      }),
    },
  ),
);
