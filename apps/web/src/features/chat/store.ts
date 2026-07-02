import { create } from "zustand";

interface InFlightStream {
  threadId: string;
  assistantId: string;
  text: string;
}

interface ChatState {
  inFlight: InFlightStream | null;
  startStream: (threadId: string, assistantId: string) => void;
  appendStream: (chunk: string) => void;
  endStream: () => void;
  failStream: (error: string) => void;
  clearInFlight: () => void;
}

export const useChatStore = create<ChatState>()((set) => ({
  inFlight: null,

  startStream: (threadId, assistantId) =>
    set({ inFlight: { threadId, assistantId, text: "" } }),

  appendStream: (chunk) =>
    set((s) => {
      if (!s.inFlight) return s;
      return { inFlight: { ...s.inFlight, text: s.inFlight.text + chunk } };
    }),

  endStream: () => set({ inFlight: null }),

  failStream: (error) =>
    set((s) => {
      if (!s.inFlight) return s;
      return {
        inFlight: { ...s.inFlight, text: s.inFlight.text + ` [${error}]` },
      };
    }),

  clearInFlight: () => set({ inFlight: null }),
}));
