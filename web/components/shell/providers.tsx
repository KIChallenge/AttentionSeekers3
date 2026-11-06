"use client";

import type { ReactNode } from "react";
import { EvidenceProvider } from "@/components/stat/evidence-panel";
import { AppSidebar } from "@/components/shell/app-sidebar";
import { PageHeader } from "@/components/shell/page-header";
import { ThemeProvider, useAppTheme } from "@/components/shell/theme";
import { UserProvider } from "@/components/shell/user-provider";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <TooltipProvider delayDuration={200}>
        <UserProvider>
          <EvidenceProvider>
            <SidebarProvider>
              <AppSidebar />
              <SidebarInset className="min-w-0">
                <PageHeader />
                {children}
              </SidebarInset>
            </SidebarProvider>
          </EvidenceProvider>
        </UserProvider>
        <ThemedToaster />
      </TooltipProvider>
    </ThemeProvider>
  );
}

function ThemedToaster() {
  const { theme } = useAppTheme();
  return <Toaster position="bottom-right" theme={theme} />;
}
