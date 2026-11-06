"use client";

import { useState } from "react";
import { useApi } from "@/hooks/use-api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useUser } from "./user-provider";

/** Choose or enter a named person. The API decides whether a name is acceptable (T7). */
export function LoginForm({ onDone }: { onDone?: () => void }) {
  const { user, setUser } = useUser();
  const users = useApi<{ users: string[]; free_entry: boolean; hint?: string }>("/api/users");
  const [name, setName] = useState(user ?? "");
  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (!name.trim()) return;
        setUser(name);
        onDone?.();
      }}
    >
      {users.data && users.data.users.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {users.data.users.map((u) => (
            <Button
              key={u}
              type="button"
              size="xs"
              variant={u === user ? "default" : "outline"}
              className="rounded-full"
              onClick={() => {
                setUser(u);
                onDone?.();
              }}
            >
              {u}
            </Button>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Vor- und Nachname" aria-label="Name der Person" />
        <Button type="submit" size="sm" disabled={!name.trim()}>
          Anmelden
        </Button>
      </div>
      {users.data?.hint && <p className="text-xs text-muted-foreground">{users.data.hint}</p>}
    </form>
  );
}
