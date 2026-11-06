"use client";

import { ArrowDown01Icon, Logout01Icon, Moon02Icon, Sun03Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { useState } from "react";
import { useApi } from "@/hooks/use-api";
import type { Health } from "@/lib/types";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Separator } from "@/components/ui/separator";
import {
  SidebarFooter,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { LoginForm } from "./login-form";
import { useAppTheme } from "./theme";
import { useUser } from "./user-provider";

export function initials(name: string) {
  return name
    .split(/\s+/)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function ShellSidebarFooter() {
  const { user, setUser } = useUser();
  const { theme, toggle } = useAppTheme();
  const { isMobile } = useSidebar();
  const [open, setOpen] = useState(false);
  const health = useApi<Health>("/api/health");
  const mode = health.error
    ? "Backend nicht erreichbar"
    : health.data
      ? health.data.llm.configured
        ? `Agent: ${health.data.llm.deployment ?? "Sprachmodell"}`
        : "Offline-Modus"
      : "Verbindung wird geprüft …";
  const dark = theme === "dark";
  return (
    <SidebarFooter className="mt-auto px-3 pb-3 pt-1 group-data-[collapsible=icon]:px-2">
      <SidebarMenu>
        <SidebarMenuItem>
          <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
              <SidebarMenuButton
                size="lg"
                tooltip="Angemeldete Person und Einstellungen"
                className="h-11 gap-2 rounded-[10px] px-2 text-foreground hover:bg-sidebar-accent data-open:bg-sidebar-accent group-data-[collapsible=icon]:h-8"
                aria-label={user ? `${user}, Einstellungen` : "Anmelden"}
              >
                <Avatar className="size-6 shrink-0 rounded-md">
                  <AvatarFallback className="rounded-md bg-muted text-[10px] font-medium text-foreground">
                    {user ? initials(user) : "?"}
                  </AvatarFallback>
                </Avatar>
                <SidebarGroupContent className="min-w-0 flex-1 group-data-[collapsible=icon]:hidden [&>span]:block [&>span]:truncate [&>span:first-child]:font-medium [&>span:last-child]:text-xs [&>span:last-child]:text-muted-foreground">
                  <span>{user ?? "Nicht angemeldet"}</span>
                  <span title={health.data?.llm.mode_label}>{mode}</span>
                </SidebarGroupContent>
                <HugeiconsIcon icon={ArrowDown01Icon} strokeWidth={2} className="ml-auto group-data-[collapsible=icon]:hidden" />
              </SidebarMenuButton>
            </PopoverTrigger>
            <PopoverContent side={isMobile ? "top" : "right"} align="end" className="w-80 gap-1 p-1">
              <div className="flex flex-col gap-2 p-2">
                <p className="text-xs font-medium text-muted-foreground">Person für Freigaben (T7)</p>
                <LoginForm onDone={() => setOpen(false)} />
              </div>
              {user && (
                <Button variant="ghost" className="justify-start" onClick={() => setUser(null)}>
                  <HugeiconsIcon icon={Logout01Icon} strokeWidth={2} />
                  Abmelden
                </Button>
              )}
              <Separator />
              <Button variant="ghost" className="justify-start" onClick={toggle}>
                <HugeiconsIcon icon={dark ? Sun03Icon : Moon02Icon} strokeWidth={2} />
                {dark ? "Helles Design" : "Dunkles Design"}
              </Button>
              <Separator />
              <div className="px-2 py-1.5 text-xs text-muted-foreground">
                {health.data ? health.data.llm.mode_label : mode}
                {health.data?.db && <div className="mt-1">Datenbank: {health.data.db.db} · PostgreSQL</div>}
              </div>
            </PopoverContent>
          </Popover>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarFooter>
  );
}
