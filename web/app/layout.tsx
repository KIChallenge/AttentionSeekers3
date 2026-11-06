import "@fontsource-variable/inter";
import { GeistMono } from "geist/font/mono";
import type { Metadata } from "next";
import "@xyflow/react/dist/style.css";

import "./app.css";
import { cn } from "@/lib/utils";
import { Providers } from "@/components/shell/providers";
import { THEME_SCRIPT } from "@/lib/theme-script";

export const metadata: Metadata = {
  title: "StatAgent · Beschäftigungsstatistik",
  description: "Amtliche Beschäftigungsstatistik aus 24 Monatslieferungen – jede Zahl mit Quellennachweis.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="de" className={cn(GeistMono.variable, "font-sans")} suppressHydrationWarning>
      <head>
        {/* static theme script (as in medlyn) – runs before hydration to avoid a flash */}
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
