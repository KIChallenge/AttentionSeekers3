"use client";

import { cn } from "@/lib/utils";

/** Small labelled on/off switch (button role=switch, keyboard accessible). */
export function Switch({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="flex items-center gap-2 rounded-full px-2 py-1 text-xs text-muted-foreground outline-offset-2 hover:text-foreground focus-visible:outline-1"
    >
      <span className={cn("relative h-4 w-7 rounded-full transition-colors", checked ? "bg-foreground" : "bg-gray-alpha-300")}>
        <span className={cn("absolute top-0.5 size-3 rounded-full bg-background transition-all", checked ? "left-3.5" : "left-0.5")} />
      </span>
      {label}
    </button>
  );
}
