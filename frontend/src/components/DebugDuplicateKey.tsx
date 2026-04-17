"use client";

/**
 * DEBUG ONLY — remove after finding the NaN key source.
 * Intercepts React's duplicate-key warning and re-logs it with a full
 * console.trace() so the component responsible appears in DevTools.
 */
import { useEffect } from "react";

export function DebugDuplicateKey() {
  useEffect(() => {
    const original = console.error.bind(console);
    console.error = (...args: unknown[]) => {
      const msg = args[0];
      if (typeof msg === "string" && msg.includes("same key") && String(args[1]).includes("NaN")) {
        original("🔍 [DebugDuplicateKey] NaN key warning intercepted — see trace below:");
        console.trace();
      }
      original(...args);
    };
    return () => {
      console.error = original;
    };
  }, []);

  return null;
}
