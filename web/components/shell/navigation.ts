import {
  AiBrain01Icon,
  AiChat02Icon,
  ChartLineData01Icon,
  CheckListIcon,
  DashboardSquare01Icon,
  Download04Icon,
  File02Icon,
  Home01Icon,
  Layers01Icon,
  PlayCircleIcon,
  RoboticIcon,
  Task01Icon,
  TickDouble02Icon,
  UserGroupIcon,
} from "@hugeicons/core-free-icons";

export const navigation = [
  {
    label: "Produktion",
    items: [
      { title: "Übersicht", href: "/", icon: Home01Icon },
      { title: "Lieferungen", href: "/lieferungen", icon: File02Icon },
      { title: "Läufe", href: "/laeufe", icon: PlayCircleIcon },
      { title: "Qualitätsberichte", href: "/qualitaetsberichte", icon: CheckListIcon },
      { title: "Klassifikationen", href: "/klassifikationen", icon: Layers01Icon },
      { title: "Pensionen", href: "/pensionen", icon: UserGroupIcon },
    ],
  },
  {
    label: "Auswertung",
    items: [
      { title: "Dashboard", href: "/dashboard", icon: DashboardSquare01Icon },
      { title: "Modelle", href: "/modelle", icon: AiBrain01Icon },
      { title: "Fragen", href: "/fragen", icon: AiChat02Icon },
      { title: "Exporte", href: "/exporte", icon: Download04Icon },
    ],
  },
  {
    label: "Steuerung",
    items: [
      { title: "Agent", href: "/agent", icon: RoboticIcon },
      { title: "Freigaben", href: "/freigaben", icon: TickDouble02Icon },
      { title: "Protokoll", href: "/protokoll", icon: Task01Icon },
    ],
  },
];

export const allNavItems = navigation.flatMap((g) => g.items);

export function routeTitle(pathname: string) {
  const exact = allNavItems.find((i) => i.href === pathname);
  if (exact) return exact.title;
  const prefix = allNavItems.filter((i) => i.href !== "/" && pathname.startsWith(i.href)).sort((a, b) => b.href.length - a.href.length)[0];
  return prefix?.title ?? "Übersicht";
}

export { ChartLineData01Icon };
