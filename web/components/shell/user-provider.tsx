"use client";

import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from "react";

const KEY = "statagent-user";

type UserCtx = { user: string | null; setUser: (name: string | null) => void; ready: boolean };
const Ctx = createContext<UserCtx>({ user: null, setUser: () => {}, ready: false });

/** Named person for approvals (T7). Stored only in this browser. */
export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    try {
      setUserState(localStorage.getItem(KEY));
    } catch {
      /* storage blocked */
    }
    setReady(true);
  }, []);
  const setUser = useCallback((name: string | null) => {
    const v = name?.trim() || null;
    setUserState(v);
    try {
      if (v) localStorage.setItem(KEY, v);
      else localStorage.removeItem(KEY);
    } catch {
      /* storage blocked */
    }
  }, []);
  return <Ctx.Provider value={{ user, setUser, ready }}>{children}</Ctx.Provider>;
}

export const useUser = () => useContext(Ctx);
