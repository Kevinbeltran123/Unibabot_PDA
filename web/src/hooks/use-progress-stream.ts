"use client";

import * as React from "react";
import { api, getToken } from "@/lib/api-client";
import type { ProgressEvent } from "@/lib/types";

interface State {
  events: ProgressEvent[];
  status: "connecting" | "open" | "closed" | "error";
  lastEvent: ProgressEvent | null;
}

export function useProgressStream(analysisId: string | null) {
  const [state, setState] = React.useState<State>({
    events: [],
    status: "connecting",
    lastEvent: null,
  });

  React.useEffect(() => {
    if (!analysisId) return;

    const token = getToken();
    const url = `${api.eventsUrl(analysisId)}${token ? `?token=${encodeURIComponent(token)}` : ""}`;
    let es: EventSource | null = null;

    try {
      es = new EventSource(url);
    } catch {
      setState((s) => ({ ...s, status: "error" }));
      return;
    }

    es.onopen = () => setState((s) => ({ ...s, status: "open" }));

    es.onmessage = (msg) => {
      try {
        const parsed = JSON.parse(msg.data) as ProgressEvent;
        setState((s) => ({
          events: [...s.events, parsed],
          status: "open",
          lastEvent: parsed,
        }));
        if (parsed.event === "complete" || parsed.event === "error" || parsed.event === "done") {
          es?.close();
          setState((s) => ({ ...s, status: "closed" }));
        }
      } catch {
        /* ignore */
      }
    };

    es.onerror = () => {
      setState((s) => ({ ...s, status: s.events.length > 0 ? "closed" : "error" }));
      es?.close();
    };

    return () => {
      es?.close();
    };
  }, [analysisId]);

  return state;
}
