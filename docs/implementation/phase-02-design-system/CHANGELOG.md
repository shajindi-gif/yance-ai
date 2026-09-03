# Phase 2 Changelog — Enterprise Design System

Status: locally verified; hosted CI remains required before release.

## Changed

- Added a persistent authenticated workspace shell with desktop navigation, a responsive mobile
  drawer, active-route state, workspace identity and a single logout boundary.
- Separated authenticated product chrome from the public website. Dashboard, task, report and
  billing-history routes no longer render the marketing header, footer or floating assistant;
  public pages retain them.
- Added scoped, reusable UI primitives for buttons, badges, surfaces, page headers, empty states,
  inline alerts, loading skeletons and responsive data tables.
- Added centralized workspace navigation metadata. Only routes backed by current frontend and API
  behavior are links; future Opportunities, Companies, Documents, Agents, Settings and Admin
  destinations are explicitly non-interactive roadmap context.
- Migrated dashboard, task list, task detail, reports and billing history into the workspace shell
  with consistent loading, error and empty states.
- Centralized task and download API contracts in the shared client, including typed task details,
  persisted deliverables, run summaries, next actions and review mutations.
- Replaced the task revision browser prompt with an accessible, editable review form. Quality
  scores are displayed only when a persisted value exists; otherwise the product says that no
  evaluation data exists.
- Removed the unused frontend demo-payment client method. Orders, reports and tasks show only
  server-returned records and do not synthesize activity or product metrics.
- Removed external Google Fonts requests and use a system font stack, reducing a third-party
  runtime dependency and avoiding a font-loading layout shift.
- Added mobile overflow fixes and improved focus, label and contrast behavior on the migrated
  workspace surfaces.

## Verification

- Next.js 16.3.4 production build and TypeScript validation: pass for 26 routes.
- Frontend standalone runtime artifact: present.
- Full backend regression suite: 28 passed.
- Backend Ruff gate: pass.
- Repository whitespace check: pass.
- Desktop browser smoke at 1280 px: dashboard, tasks, task detail, reports and billing history
  rendered meaningful content with no framework overlay and without marketing chrome.
- Mobile browser smoke at 390 x 844: workspace drawer opened correctly and horizontal overflow was
  eliminated.
- Public homepage smoke: marketing header, footer and assistant remained present; no request to
  `fonts.googleapis.com` was observed.
- Automated WCAG A/AA scan on dashboard and task detail: zero reported violations after label and
  contrast corrections. The scanner left one incomplete manual-review group on each page; this is
  not represented as a full accessibility certification.
- Task-detail review form: keyboard-addressable textarea and submit/cancel controls rendered and
  were named correctly.

Browser API responses used for these visual-state checks were temporary, same-origin test fixtures
and were clearly labeled as test data. They were never written into the product or database and are
not represented as customer usage.

## Compatibility and migration

- No database migration.
- No backend API shape change.
- Existing public and product URLs remain stable.
- The change is reversible as one frontend commit without transforming customer data.

## Remaining design debt

- `website/app/globals.css` remains a 5,357-line legacy stylesheet with duplicate public-site
  selectors. Removing it safely requires migrating each remaining consumer; this phase does not
  claim that cleanup is complete.
- Public marketing, onboarding, checkout and several legacy product pages still contain inline
  styles. The five migrated workspace pages reduced their inline style objects to four total, all
  used for dynamic score/skeleton presentation.
- The current root layout chooses public versus workspace chrome on the client. Next.js route groups
  should replace this boundary later to avoid shipping unused public chrome in the initial React
  payload for authenticated pages.
- This phase provides visual and interaction consistency only. It does not claim that Company,
  Opportunity, Application, Agent, Admin, Eval or enterprise billing workflows exist; those remain
  gated by their implementation phases.

## Exit status

Phase 2 is complete for the currently working authenticated routes. The project builds, the backend
regression suite remains green, existing URLs are preserved, unimplemented destinations are not
clickable, and test-only browser fixtures have not entered product data. Release still requires a
successful hosted root CI run.
