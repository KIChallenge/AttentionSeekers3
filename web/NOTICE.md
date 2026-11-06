# Notice – third-party design

The look and feel of this web frontend is copied from **medlyn** by Julian-AT
(<https://github.com/Julian-AT/medlyn>, `apps/app`), licensed under
**CC BY-NC 4.0** (<https://creativecommons.org/licenses/by-nc/4.0/>) and used
**with the author's permission**, for **non-commercial** use only (KI Challenge 2026).

Copied unchanged from medlyn `apps/app`:

- `app/globals.css` (design tokens, typography, focus styles)
- `components/ui/*` (shadcn/ui components, style `radix-luma`, base `neutral`)
- `components.json`, `hooks/use-mobile.ts`

Adapted from medlyn (structure and class names kept, content German/StatAgent-specific):

- shell: `components/shell/app-sidebar.tsx`, `page-header.tsx`, `sidebar-footer.tsx`, `command-search.tsx`
- `components/stat/page-shell.tsx` (PageShell, PageHeading), `components/stat/shimmer.tsx`,
  evidence chips and the Quellennachweis panel (after medlyn's source chips / evidence sheet)

Changes: `lib/utils.ts` uses `clsx` + `tailwind-merge` instead of the `cn` package; the brand
mark is our own; fonts are self-hosted (`@fontsource-variable/inter`, `geist`) instead of
`next/font/google` so the app works offline. Our additions live in `app/app.css`.
