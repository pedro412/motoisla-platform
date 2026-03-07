"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

type PrinterStatus = "idle" | "printing" | "error";

interface PrinterState {
  // Persisted
  charWidth: 32 | 42 | 48;
  storeAddress: string;
  storePhone: string;
  // Runtime (not persisted)
  status: PrinterStatus;
  errorMessage: string | null;

  setCharWidth: (w: 32 | 42 | 48) => void;
  setStoreAddress: (a: string) => void;
  setStorePhone: (p: string) => void;
  setStatus: (status: PrinterStatus, message?: string) => void;
}

export const usePrinterStore = create<PrinterState>()(
  persist(
    (set) => ({
      charWidth: 42,
      storeAddress: "",
      storePhone: "",
      status: "idle",
      errorMessage: null,

      setCharWidth: (w) => set({ charWidth: w }),
      setStoreAddress: (a) => set({ storeAddress: a }),
      setStorePhone: (p) => set({ storePhone: p }),
      setStatus: (status, message) =>
        set({ status, errorMessage: message ?? null }),
    }),
    {
      name: "motoisla-printer",
      partialize: (state) => ({
        charWidth: state.charWidth,
        storeAddress: state.storeAddress,
        storePhone: state.storePhone,
      }),
    },
  ),
);
