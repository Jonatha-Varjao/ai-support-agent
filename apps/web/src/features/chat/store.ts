import { create } from "zustand";

interface InFlightStream {
  threadId: string;
  userContent: string;
  text: string;
  createdAt: string;
}

interface ChatState {
  inFlight: InFlightStream | null;
  startStream: (threadId: string, userContent: string) => void;
  appendStream: (chunk: string) => void;
  clearInFlight: () => void;
}

export const useChatStore = create<ChatState>()((set) => ({
  inFlight: null,

  startStream: (threadId, userContent) =>
    set({ inFlight: { threadId, userContent, text: "", createdAt: new Date().toISOString() } }),

  appendStream: (chunk) =>
    set((s) => {
      if (!s.inFlight) return s;
      return { inFlight: { ...s.inFlight, text: s.inFlight.text + chunk } };
    }),

  clearInFlight: () => set({ inFlight: null }),
}));
