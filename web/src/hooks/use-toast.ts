"use client";

import * as React from "react";
import type { ToastProps } from "@/components/ui/toast";

type ToasterToast = ToastProps & {
  id: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
};

const TOAST_LIMIT = 4;
const TOAST_REMOVE_DELAY = 5000;

type State = { toasts: ToasterToast[] };

let count = 0;
function genId(): string {
  count = (count + 1) % Number.MAX_SAFE_INTEGER;
  return count.toString();
}

const listeners: Array<(state: State) => void> = [];
let memoryState: State = { toasts: [] };

function dispatch(action: { type: "ADD"; toast: ToasterToast } | { type: "REMOVE"; toastId: string }) {
  if (action.type === "ADD") {
    memoryState = { toasts: [action.toast, ...memoryState.toasts].slice(0, TOAST_LIMIT) };
  } else {
    memoryState = { toasts: memoryState.toasts.filter((t) => t.id !== action.toastId) };
  }
  listeners.forEach((l) => l(memoryState));
}

type ToastOptions = Omit<ToasterToast, "id">;

export function toast(opts: ToastOptions) {
  const id = genId();
  const t: ToasterToast = { ...opts, id, open: true };
  dispatch({ type: "ADD", toast: t });
  setTimeout(() => dispatch({ type: "REMOVE", toastId: id }), TOAST_REMOVE_DELAY);
  return id;
}

export function useToast() {
  const [state, setState] = React.useState<State>(memoryState);
  React.useEffect(() => {
    listeners.push(setState);
    return () => {
      const idx = listeners.indexOf(setState);
      if (idx > -1) listeners.splice(idx, 1);
    };
  }, []);
  return { ...state, toast };
}
