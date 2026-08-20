# Refactor Frontend Sidebar and Aesthetic with shadcn sidebar-08 & b1GdfqsQE Preset

## Context & User Directives

- **User Directives**:
  - Apply shadcn preset `b1GdfqsQE` (translucent menus, subtle accents, medium radius, neutral theme with amber highlights, clean mira styling).
  - Reference `sidebar-08` from shadcn to redesign the current sidebar framework (inset layout, structured `NavMain`, `NavLanes`, `NavSecondary`, `NavHarness` user/status footer, breadcrumbs in `SidebarInset`).
  - Integrate both designs cleanly without breaking existing components or theme system; adapt specifically for the HITL research system.
  - Run via LFG workflow without creating a PR on GitHub (stay in current branch).

---

## Technical Design & Architecture

### 1. Preset `b1GdfqsQE` Aesthetic Tokens

- **Menu & Backgrounds**: Translucent glassmorphism (`backdrop-blur-md bg-background/80`, `bg-sidebar/80`), subtle borders (`border-border/60`).
- **Accents**: Subtle hover/active states (`hover:bg-muted/50`, `bg-accent/60 text-accent-foreground`).
- **Radius**: Consistent medium radius (`rounded-lg` / `rounded-md`).
- **Attention Highlights**: Amber accent tokens for pending / attention / alert states in HITL workflow.

### 2. `sidebar-08` Inset Architecture

- **Sidebar Variant**: `variant="inset"` with `<SidebarInset>` floating container wrapper in `App.tsx`.
- **Top Header**: Sticky header in `SidebarInset` containing:
  - `<SidebarTrigger />`
  - `<Separator orientation="vertical" className="mr-2 h-4" />`
  - `<Breadcrumb>` (`MedRec Research` > `HITL Control` > `[Section Name]`)
  - Snapshot SHA, Condition, and Schema version chips.
- **Sidebar Header**: Branded workspace header with logo, title, and environment indicator.
- **NavMain**: Primary navigation with icon, label, and active status indicators.
- **NavLanes**: Quick overview of research lanes (SafeDrug, GAMENet, RETAIN, MoleRec, LEAP).
- **NavSecondary**: Secondary navigation (Fail-Closed Protocol, Research Memory, 319 Specs) pinned at `mt-auto`.
- **NavHarness**: Footer harness status card displaying current condition, snapshot hash, and fail-closed badge.

---

## Implementation Units

- [x] **U1: Create UI Breadcrumb Component (`web/src/components/ui/breadcrumb.tsx`)**
  - Implement accessible `Breadcrumb`, `BreadcrumbList`, `BreadcrumbItem`, `BreadcrumbLink`, `BreadcrumbPage`, `BreadcrumbSeparator` using Tailwind v4 and Tabler icons.
- [x] **U2: Refactor AppSidebar with sidebar-08 Structure (`web/src/components/app-sidebar.tsx`)**
  - Implement `Sidebar` with `variant="inset"`, `SidebarHeader`, `NavMain`, `NavLanes`, `NavSecondary`, and `NavHarness` footer.
- [x] **U3: Refactor App Layout with SidebarInset & Header (`web/src/App.tsx`)**
  - Wrap main content in `<SidebarInset className="overflow-hidden">`.
  - Add top breadcrumb header with `SidebarTrigger`, `Separator`, and status metadata.
- [x] **U4: Refactor Console Toolbar & Glassmorphism Details (`web/src/components/console-toolbar.tsx`)**
  - Apply `b1GdfqsQE` subtle translucent styling and refined input/button radii.
- [x] **U5: Frontend Verification**
  - Run `npm test`, `npm run typecheck`, `npm run lint`, `npm run format:check`, and `npm run build`.

---

## Verification Plan

1. Vitest tests (`npm test`) in `web/` pass 100%.
2. TypeScript compilation (`npm run typecheck`) passes with 0 errors.
3. ESLint & Prettier (`npm run lint && npm run format:check`) pass cleanly.
4. Production build (`npm run build`) generates clean bundle without build drift.
5. Python backend checks (`pytest`, `ruff`, `markdownlint`) pass with 0 regressions.
