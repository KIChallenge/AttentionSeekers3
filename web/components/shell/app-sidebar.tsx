"use client";

import { HugeiconsIcon } from "@hugeicons/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useApi } from "@/hooks/use-api";
import type { Overview } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar";
import { BrandMark } from "./brand-mark";
import { navigation } from "./navigation";
import { ShellSidebarFooter } from "./sidebar-footer";

export function AppSidebar() {
  const pathname = usePathname();
  const { setOpenMobile } = useSidebar();
  const overview = useApi<Overview>("/api/overview");
  const badges: Record<string, number | undefined> = {
    "/freigaben": overview.data?.stats.rules_proposed || undefined,
  };
  return (
    <Sidebar collapsible="icon" className="print:hidden">
      <SidebarHeader className="h-[50px] justify-center px-3 py-0 group-data-[collapsible=icon]:px-2">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              tooltip="StatAgent"
              className="h-8 gap-2 px-2 text-base font-semibold tracking-normal text-foreground hover:bg-transparent active:bg-transparent"
            >
              <Link href="/" onClick={() => setOpenMobile(false)}>
                <BrandMark />
                <span>StatAgent</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent className="gap-5 pt-1 pb-3 [&_[data-slot=sidebar-menu]]:gap-1">
        {navigation.map((group) => (
          <SidebarGroup key={group.label} className="p-0 px-3 group-data-[collapsible=icon]:px-2">
            <SidebarGroupLabel className="mb-1.5 h-5 rounded-[10px] px-1.5 text-sm/5 font-medium text-sidebar-foreground group-data-[collapsible=icon]:hidden">
              {group.label}
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => {
                  const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                  const count = badges[item.href];
                  return (
                    <SidebarMenuItem key={item.href}>
                      <SidebarMenuButton
                        asChild
                        isActive={active}
                        tooltip={item.title}
                        className={cn(
                          "h-8 gap-2 rounded-[10px] px-2 text-sm/5 font-medium text-sidebar-foreground hover:text-foreground [&_svg]:size-[18px] [&_svg]:text-sidebar-foreground",
                          "data-active:bg-sidebar-accent data-active:text-foreground data-active:[&_svg]:text-foreground",
                        )}
                      >
                        <Link href={item.href} aria-current={active ? "page" : undefined} onClick={() => setOpenMobile(false)}>
                          <span className="-mx-0.5 flex h-8 min-w-5 shrink-0 items-center justify-center">
                            <HugeiconsIcon icon={item.icon} strokeWidth={2} />
                          </span>
                          <span className="truncate">{item.title}</span>
                        </Link>
                      </SidebarMenuButton>
                      {count !== undefined && (
                        <SidebarMenuBadge className="bg-warning/10 text-warning" aria-label={`${count} offene Freigaben`}>
                          {count}
                        </SidebarMenuBadge>
                      )}
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <ShellSidebarFooter />
      <SidebarRail />
    </Sidebar>
  );
}
