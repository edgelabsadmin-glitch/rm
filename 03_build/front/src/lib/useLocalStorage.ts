/*
 * SPEC-035 — tiny localStorage-backed state (Q36: persist Action Queue filter
 * selections across sessions). The only client-persistence need in Phase 1
 * (audit D7: no IndexedDB).
 */
import { useEffect, useState } from "react";

export function useLocalStorage<T>(key: string, initial: T): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? (JSON.parse(raw) as T) : initial;
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* quota / private mode — non-fatal */
    }
  }, [key, value]);
  return [value, setValue];
}
