import { create } from "zustand";

interface AdminState {
  is_admin: boolean;
  setAdmin: (val: boolean, token?: string) => void;
}

const adminStore = create<AdminState>((set) => ({
  is_admin: false,
  setAdmin: (val, token) => {
    if (val && token) {
      localStorage.setItem("token", token);
      set({ is_admin: true });
    } else {
      localStorage.removeItem("token");
      if (typeof window != "undefined") window.location.replace("/home");
    }
  },
}));

export default adminStore;
