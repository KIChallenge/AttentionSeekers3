"use client";

import { type ElementType, memo } from "react";
import { CardDescription } from "@/components/ui/card";
import { cn } from "@/lib/utils";

// Copied from medlyn (components/ai-elements/shimmer.tsx), CC BY-NC 4.0.
export const Shimmer = memo(function Shimmer({
  children,
  as: Component = CardDescription,
  className,
}: {
  children: string;
  as?: ElementType;
  className?: string;
}) {
  return (
    <Component
      className={cn(
        "bg-linear-to-r from-muted-foreground via-primary to-muted-foreground bg-clip-text text-transparent motion-safe:animate-pulse",
        className,
      )}
    >
      {children}
    </Component>
  );
});
