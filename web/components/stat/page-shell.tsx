import type { ReactNode } from "react";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function PageShell({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  return (
    <Card
      className={cn(
        "mx-auto w-full min-w-0 gap-6 overflow-visible rounded-none bg-transparent px-4 py-6 shadow-none ring-0 md:px-8 md:py-8",
        wide ? "max-w-[1400px]" : "max-w-[1100px]",
      )}
    >
      <CardContent className="flex min-w-0 flex-col gap-6 px-0">{children}</CardContent>
    </Card>
  );
}

export function PageHeading({ title, description, action }: { title: string; description: ReactNode; action?: ReactNode }) {
  return (
    <Card className="gap-0 overflow-visible rounded-none bg-transparent py-0 shadow-none ring-0">
      <CardHeader className="gap-y-2 px-0">
        <CardTitle className="text-2xl font-semibold" role="heading" aria-level={1}>
          {title}
        </CardTitle>
        <CardDescription className="max-w-2xl text-sm/5">{description}</CardDescription>
        {action && (
          <CardAction className="self-center max-sm:col-start-1 max-sm:row-start-3 max-sm:mt-2 max-sm:justify-self-start">{action}</CardAction>
        )}
      </CardHeader>
    </Card>
  );
}

/** Bordered panel used across pages (medlyn: rounded-2xl, border, no shadow). */
export function Panel({
  title,
  description,
  action,
  children,
  className,
  contentClassName,
}: {
  title?: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
}) {
  return (
    <Card className={cn("min-w-0 gap-4 rounded-2xl border border-border bg-card p-4 shadow-none ring-0", className)}>
      {(title || action) && (
        <CardHeader className="gap-1 p-0">
          {title && <CardTitle className="text-sm font-semibold">{title}</CardTitle>}
          {description && <CardDescription className="text-xs">{description}</CardDescription>}
          {action && <CardAction>{action}</CardAction>}
        </CardHeader>
      )}
      <CardContent className={cn("flex min-w-0 flex-col gap-3 p-0", contentClassName)}>{children}</CardContent>
    </Card>
  );
}

export function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <h2 className="text-base font-semibold">{children}</h2>
      {action}
    </div>
  );
}
