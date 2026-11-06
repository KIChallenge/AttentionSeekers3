"use client";

import { CheckListIcon, File02Icon, Search01Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useApi } from "@/hooks/use-api";
import { fmtMonth } from "@/lib/format";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Kbd } from "@/components/ui/kbd";
import { allNavItems } from "./navigation";

const icon = (glyph: typeof Search01Icon) => <HugeiconsIcon icon={glyph} strokeWidth={2} className="text-muted-foreground" />;

export function CommandSearch() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const months = useApi<{ months: string[] }>(open ? "/api/statistik/monate?regelwerk=basis" : null);
  const rules = useApi<{ rules: { rule_id: string; title: string }[] }>(open ? "/api/regeln" : null);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key.toLowerCase() !== "k" || !(event.metaKey || event.ctrlKey)) return;
      event.preventDefault();
      setOpen((c) => !c);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const go = (href: string) => {
    setOpen(false);
    router.push(href);
  };

  return (
    <>
      <Button
        variant="ghost"
        onClick={() => setOpen(true)}
        className="h-8 w-44 justify-start gap-2 rounded-[10px] bg-muted px-2.5 text-sm font-normal text-muted-foreground shadow-none hover:bg-accent sm:w-56"
        aria-label="Suche öffnen (Strg+K)"
      >
        {icon(Search01Icon)}
        <span className="flex-1 text-left">Suchen</span>
        <Kbd>Strg K</Kbd>
      </Button>
      <CommandDialog open={open} onOpenChange={setOpen} title="StatAgent durchsuchen" description="Seiten, Qualitätsberichte und Regeln">
        <Command>
          <CommandInput placeholder="Seite, Monat (z. B. 2025-06) oder Regel suchen …" />
          <CommandList>
            <CommandEmpty>Keine Treffer.</CommandEmpty>
            <CommandGroup heading="Seiten">
              {allNavItems.map((item) => (
                <CommandItem key={item.href} value={`seite ${item.title}`} onSelect={() => go(item.href)}>
                  {icon(item.icon)}
                  {item.title}
                </CommandItem>
              ))}
            </CommandGroup>
            {months.data && (
              <CommandGroup heading="Qualitätsberichte">
                {months.data.months.map((m) => (
                  <CommandItem key={m} value={`qualitätsbericht qb ${m} ${fmtMonth(m)}`} onSelect={() => go(`/qualitaetsberichte?monat=${m}`)}>
                    {icon(CheckListIcon)}
                    QB {fmtMonth(m)} <span className="ml-auto font-mono text-xs text-muted-foreground">{m}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
            {rules.data && (
              <CommandGroup heading="Regeln">
                {rules.data.rules.map((r) => (
                  <CommandItem key={r.rule_id} value={`regel ${r.rule_id} ${r.title}`} onSelect={() => go(`/freigaben?regel=${r.rule_id}`)}>
                    {icon(File02Icon)}
                    <span className="font-mono text-xs">{r.rule_id}</span>
                    <span className="truncate">{r.title}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </CommandDialog>
    </>
  );
}
