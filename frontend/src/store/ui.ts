import { create } from "zustand";

export type ToastItem = { id: number; title: string; tone?: "ok" | "warn" | "err" };

type UiState = {
  sidebarOpen: boolean;
  commandOpen: boolean;
  tourOpen: boolean;
  toasts: ToastItem[];
  toggleSidebar: () => void;
  setCommand: (v: boolean) => void;
  setTour: (v: boolean) => void;
  toast: (title: string, tone?: ToastItem["tone"]) => void;
  dismiss: (id: number) => void;
};

let n = 1;

export const useUi = create<UiState>((set, get) => ({
  sidebarOpen: true,
  commandOpen: false,
  tourOpen: false,
  toasts: [],
  toggleSidebar: () => set({ sidebarOpen: !get().sidebarOpen }),
  setCommand: (v) => set({ commandOpen: v }),
  setTour: (v) => set({ tourOpen: v }),
  toast: (title, tone = "ok") => {
    const id = n++;
    set({ toasts: [...get().toasts, { id, title, tone }] });
    window.setTimeout(() => get().dismiss(id), 4200);
  },
  dismiss: (id) => set({ toasts: get().toasts.filter((t) => t.id !== id) }),
}));
