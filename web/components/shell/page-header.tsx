"use client";

import { AiChat02Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { CommandSearch } from "./command-search";
import { routeTitle } from "./navigation";

export function PageHeader() {
  const pathname = usePathname();
  return (
    <Card className="sticky top-0 z-20 shrink-0 gap-0 rounded-none border-0 border-b bg-background/90 py-0 shadow-none ring-0 backdrop-blur print:hidden">
      <CardContent className="flex h-[49px] flex-nowrap items-center gap-3 px-4">
        <SidebarTrigger aria-label="Navigation ein-/ausblenden" className="shrink-0" />
        <Separator orientation="vertical" className="data-[orientation=vertical]:h-4 data-[orientation=vertical]:self-center" />
        <Breadcrumb className="min-w-0 flex-1">
          <BreadcrumbList className="flex-nowrap gap-2 overflow-hidden whitespace-nowrap text-sm font-medium sm:gap-2">
            <BreadcrumbItem className="hidden shrink-0 sm:inline-flex">
              <BreadcrumbLink asChild>
                <Link href="/">Beschäftigungsstatistik</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator className="hidden sm:block" />
            <BreadcrumbItem className="min-w-0">
              <BreadcrumbPage className="truncate font-medium">{routeTitle(pathname)}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
        <div className="ml-auto flex shrink-0 items-center gap-2">
          <CommandSearch />
          <Button asChild size="sm" className="hidden h-8 gap-1.5 rounded-[10px] px-3 sm:inline-flex">
            <Link href="/fragen">
              <HugeiconsIcon icon={AiChat02Icon} strokeWidth={2} data-icon="inline-start" />
              Frage stellen
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
