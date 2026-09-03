# Phase 2 Implementation Plan — Enterprise Design System

## Objective

Create a credible, reusable enterprise product surface without changing the backend contract or
pretending that later workflow, Agent, admin, and billing capabilities already exist. This phase
separates the public website from the authenticated workspace, establishes one design language,
and migrates existing working pages onto shared components.

## Current-state findings

- `website/app/globals.css` is 5,357 lines and contains many repeated selector definitions; some
  base selectors are declared between two and nine times.
- Authenticated pages independently implement page width, headers, cards, badges, loading states,
  empty states, tables, and action styles. The task detail page alone has 48 inline style objects;
  orders has 28 and reports has 26.
- The root layout renders the marketing Header, Footer, and floating assistant on workspace pages,
  so the product feels like a website with tools rather than a persistent SaaS workspace.
- Navigation data is duplicated between Header and Footer, while authenticated navigation is
  duplicated within pages.
- External Google Fonts are loaded through raw `<link>` tags, adding a third-party runtime request
  and bypassing Next.js font optimization.
- Loading and empty states are inconsistent and most error states are either silent or plain text.
- Several future destinations do not exist. They must not be exposed as functional links in this
  phase.

## Change slices

1. Design foundation: semantic color, spacing, typography, radius, elevation, focus, and status
   tokens; system font stack; reduced-motion and responsive rules.
2. Shared UI primitives: Button, Badge, Surface, PageHeader, EmptyState, InlineAlert, Skeleton, and
   accessible table containers.
3. Product shell: responsive sidebar/top bar, active-route state, mobile navigation, workspace
   identity, and a single logout boundary.
4. Chrome separation: marketing Header/Footer/assistant remain on public pages and are removed from
   authenticated workspace routes.
5. Existing-page migration: dashboard, tasks, task detail, reports, and orders adopt the shell and
   shared states without changing their API behavior.
6. Verification: TypeScript/build, browser checks at desktop and mobile widths, keyboard/focus
   checks, empty/error/loading state checks, and React best-practices review.

## Navigation rule

Only destinations backed by current code are interactive in Phase 2:

- Home → `/dashboard`
- Applications / Tasks → `/tasks`
- Reports → `/reports`
- Billing history → `/orders`

Opportunities, Companies, Documents, Agents, Usage, Settings, and Admin will be introduced by their
own product phases once their route and backend contract exist. They may appear only as clearly
non-interactive roadmap context, never as working buttons.

## Files

- `website/app/layout.tsx`
- `website/app/globals.css`
- `website/components/SiteChrome.tsx`
- `website/components/ui/*`
- `website/components/workspace/*`
- `website/app/{dashboard,tasks,reports,orders}/page.tsx`
- `website/app/tasks/[taskId]/page.tsx`
- `website/lib/api.ts`
- `website/lib/navigation.ts`

## Compatibility and migration

- No database migration.
- No API shape change.
- Existing URLs remain stable.
- Existing marketing styles remain available while migrated workspace styles move to scoped CSS
  modules. Monolithic CSS removal is deferred until every consumer is migrated.

## Exit gates

- Production build and TypeScript pass.
- Existing backend suite remains green.
- Workspace pages show no marketing chrome or floating assistant.
- Public pages retain marketing navigation and footer.
- Desktop and mobile browser checks show meaningful content and no framework error overlay.
- No new clickable control points to an unimplemented route or mutation.
- Phase changelog records migrated files, remaining legacy CSS, and browser evidence.

## Rollback

All changes are frontend-only and preserve route/API contracts. Reverting the Phase 2 commit
restores the previous page-local presentation without data migration or business-record changes.
