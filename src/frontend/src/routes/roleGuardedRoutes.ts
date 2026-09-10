import type { TenantRole } from '@/api/types';

/**
 * The route × backend-gate decision table (#1261).
 *
 * ## Why a table and not "we added the guard where it was needed"
 *
 * Adding a role guard to the one route that motivated the issue would reproduce
 * the defect it fixes one level up: a guard applied at the call site, on the
 * routes somebody happened to look at. That is the most expensive recurring
 * failure in this repository — #948 repaired two of four sibling routes and the
 * other two stayed open for months. So the unit of work is not "the guarded
 * routes" but **every** route, each carrying a recorded decision, with
 * `scripts/check_route_role_guards.py` refusing a route that carries none.
 *
 * ## How the decisions were derived (reproducible)
 *
 * Every `require_tenant_role` / `require_permission` / `require_admin_scope`
 * dependency on the mounted FastAPI app (216 gated operations of 789) was
 * resolved by walking `app.routes` through the `_IncludedRouter` wrappers, then
 * joined against the frontend by following each route's page through its import
 * graph to the `src/api/endpoints/*` functions it can reach, and matching those
 * on method + path. Measured on `develop` @ b23f39400, 2026-09-01.
 *
 * ## The measurement that decided the shape of the guard
 *
 * **No route in this application qualifies for a whole-route block.** Every single
 * route that carries a gated write also serves reads that are open to every
 * tenant member by design — reads are open by REQ-049 §2.3, and #1260 kept
 * `GET /identification/history` open on purpose while gating the three writes
 * beside it. Blocking or redirecting would take away read access the API grants:
 * a frontend guard that is *looser* than the API is a security bug, one that is
 * *stricter* is a usability bug. {@link RequireRole} therefore restricts rather
 * than blocks, and no blocking mode exists — an unused mode is a guard with no
 * call site.
 */
export interface RoleGuardedRoute {
  /** Minimum domain role, matching the backend gate named in `gate`. */
  min: TenantRole;
  /** The backend operation whose gate this mirrors — the authority, verbatim. */
  gate: string;
}

/**
 * Routes wrapped in `<RequireRole>` in `AppRoutes.tsx`.
 *
 * The criterion is narrow and checkable: **the page's primary action — the one in
 * its `PageTitle` header — is a write the API refuses below `min`, and the rest of
 * the page is a read of that action's results.** Those are the pages where a
 * refused member would otherwise start a flow that can only end in a 403, which is
 * exactly the report in #1261. Restricting them removes the header action (via
 * {@link useRoleRestriction}, read centrally by `PageTitle`) and leaves the reads.
 *
 * A route is *not* listed here merely because it reaches a gated endpoint — 40 do.
 * See {@link ACTION_GATED_ROUTES}.
 */
export const ROLE_GUARDED_ROUTES: Readonly<Record<string, RoleGuardedRoute>> = {
  // REQ-029 — the route #1261 was filed about. Header action opens the
  // identification wizard; the body is the identification history, which
  // `GET /identification/history` keeps open to every member (#1260).
  'pflanzen/identifikation': {
    min: 'grower',
    gate: 'POST /api/v1/t/{tenant_slug}/identification/identify — require_tenant_role(grower)',
  },
  // REQ-008 — header action starts a drying run; the body lists batches with
  // drying progress and mould alerts, all open reads.
  'ernte/nachernte': {
    min: 'grower',
    gate: 'POST /api/v1/t/{tenant_slug}/post-harvest/start-drying — require_tenant_role(grower)',
  },
  // REQ-016 — header action creates equipment; the body is the equipment list
  // and the InvenTree connection status.
  inventree: {
    min: 'grower',
    gate: 'POST /api/v1/t/{tenant_slug}/equipment — require_tenant_role(grower)',
  },
  // REQ-026 — header action creates an aquaponics system; the body is water
  // quality, cycling progress and fish stocks.
  aquaponik: {
    min: 'grower',
    gate: 'POST /api/v1/t/{tenant_slug}/aquaponics/systems — require_tenant_role(grower)',
  },
  // REQ-017 — header action records a propagation event; the body is the
  // lineage/descendants graph and the event log.
  vermehrung: {
    min: 'grower',
    gate: 'POST /api/v1/t/{tenant_slug}/propagation/events — require_tenant_role(grower)',
  },
};

/**
 * Routes that reach a gated backend operation but deliberately carry **no** route
 * guard: the page is a read surface with gated actions embedded in it (a row
 * menu, a dialog, an inline control), so restricting the route would either
 * remove read access or hang a banner over a page whose write affordances the
 * banner cannot reach — a guard that is visible and inert, which is worse than
 * none. The same bucket holds the one page whose *body* is the gated write
 * (`pflanzenschutz/erkennung`): there is no read surface to leave behind
 * either, so its gate sits on the capture component, not on the route.
 *
 * These are not "done". They are the backlog of **action-level** gates, and the
 * measured gate per route is in the pull request for #1261. Moving one here to
 * {@link ROLE_GUARDED_ROUTES} is a deliberate edit that the router, the
 * parametrised test and the static check all follow automatically.
 */
export const ACTION_GATED_ROUTES: readonly string[] = [
  'settings',
  'tenants/settings',
  'ueberwinterung/profile',
  'kalender',
  'stammdaten/species',
  'stammdaten/species/:key',
  'stammdaten/companion-planting',
  'standorte/sites',
  'standorte/sites/:key',
  'standorte/locations/:key',
  'standorte/slots/:key',
  'standorte/watering-events',
  'umgebungssteuerung',
  'standorte/tanks',
  'standorte/tanks/:key',
  'pflanzen/plant-instances',
  // Also reaches the #1333-gated pest writes through `PestScanButton`; that
  // button hides itself below grower, so the gate is on the shared component,
  // not on this route.
  'pflanzen/plant-instances/:key',
  'duengung/fertilizers',
  'duengung/fertilizers/:key',
  'duengung/plans',
  'duengung/plans/:key',
  'duengung/feeding-events',
  'duengung/feeding-events/:key',
  'giessprotokoll',
  'giessprotokoll/:key',
  // #1333 — server-side gate ADDED (`POST /pests/detect` →
  // require_tenant_role(grower)), so the earlier reason "ungated server-side"
  // has expired. It stays here rather than moving to ROLE_GUARDED_ROUTES because
  // that criterion needs a read body to leave behind, and §7 omits history from
  // this page deliberately: the body *is* the gated write. `<RequireRole>`'s
  // restrict-only mode would withhold the retake button, leave the capture panel
  // standing and let a viewer reach the 403 anyway — visible and inert. The gate
  // is therefore on the capture panel itself, in PestIdentificationPage.
  'pflanzenschutz/erkennung',
  'pflanzenschutz/pests',
  'pflanzenschutz/pests/:key',
  'ernte/batches',
  'ernte/batches/:key',
  'aufgaben/queue',
  'aufgaben/tasks/:key',
  'aufgaben/workflows',
  'aufgaben/workflows/:key',
  'durchlaeufe/planting-runs',
  'durchlaeufe/planting-runs/:key',
  'durchlaeufe/succession-plans',
  'durchlaeufe/succession-plans/:key',
  'dashboard',
];

/**
 * Routes with no domain-role-gated backend operation reachable from their page,
 * measured by the join described at the top of this file. Nothing to guard.
 *
 * Three sub-cases share the bucket, all verified individually:
 * - pure redirects (`pflege`, `aufgaben/activity-plans*`) and the catch-all `*`,
 *   which have no page at all;
 * - pages that call nothing (`diagnose`, `glossar`, `kiosk`, `connect`) or only
 *   open reads (the catalogues, the substrate pages, the calculators);
 * - the DSGVO self-service (`privacy`), gated per-user on ownership rather than
 *   on any role: every member reaches their *own* data and nobody else's, so
 *   there is no rank to compare.
 *
 * The **platform-admin** surfaces (`admin/*`) used to sit in this bucket with the
 * reason "different axis, recorded as a separate gap in the #1261 pull request".
 * That gap is #1336, and they now carry their own decision in
 * {@link PLATFORM_ADMIN_ROUTES} — still the other axis, no longer undecided.
 */
export const UNGATED_ROUTES: readonly string[] = [
  'connect',
  'auth/callback',
  'login',
  'register',
  'verify-email/:token',
  'password-reset',
  'password-reset/:token',
  'kiosk',
  'privacy',
  'tenants/create',
  'invitations/accept',
  'pflege',
  'onboarding',
  'stammdaten/botanical-families',
  'stammdaten/botanical-families/:key',
  'stammdaten/species/:speciesKey/cultivars/:cultivarKey',
  'stammdaten/crop-rotation',
  'stammdaten/activities',
  'stammdaten/activities/:key',
  'stammdaten/import',
  'standorte/substrates',
  'standorte/substrates/:key',
  'standorte/substrates/batches/:key',
  'pflanzen/calculations',
  'ki-assistent',
  'glossar',
  'diagnose',
  'duengung/calculations',
  'tagebuch',
  'pflanzenschutz/diseases',
  'pflanzenschutz/treatments',
  'pflanzenschutz/treatments/:key',
  'aufgaben/activity-plans',
  'aufgaben/activity-plans/:speciesKey',
  'phasen/definitionen',
  'phasen/definitionen/:key',
  'phasen/ablaeufe',
  'phasen/ablaeufe/:key',
  '*',
];

/**
 * The platform-administration route decision (#1336, REQ-049 §2.4).
 *
 * Same defect class as {@link ROLE_GUARDED_ROUTES}, **different axis**. The
 * domain rank (viewer < grower < lead) and the platform-admin attribute are not
 * a hierarchy: `require_tenant_role`/`require_permission` never consult
 * `is_platform_admin`, and `require_platform_admin` never consults a domain
 * role. So this is a second table read by a second wrapper, not a second column
 * on the first — one component answering both questions would have to invent a
 * rank that the spec deliberately does not define.
 */
export interface PlatformAdminRoute {
  /** The backend operation whose gate this mirrors — the authority, verbatim. */
  gate: string;
}

/**
 * Routes wrapped in `<RequirePlatformAdmin>` in `AppRoutes.tsx`.
 *
 * ## The inventory (measured on `develop` @ 0575d1281, 2026-09-02)
 *
 * The survey is over the **axis**, not over the URL prefix: every frontend module
 * that calls an `/admin/...` path was traced to the pages that import it, and each
 * backend `/admin/**` operation read for its dependency. Five routes reach the
 * platform-admin gate, and only two of them are whole admin pages:
 *
 * - `admin/tenants/:key`, `admin/users/:key` — **listed below.** Every request
 *   these pages make is `require_platform_admin`, including the two `GET`s they
 *   load with. A refused member has nothing to read here at all.
 * - `settings` — the account page **every member owns**; only its *platform* and
 *   *ha* tabs are admin surfaces. It cannot be route-guarded on this axis
 *   without taking every member's own account settings away, so it keeps its
 *   domain-axis decision in {@link ACTION_GATED_ROUTES}. Measuring it did
 *   contradict the assumption this entry started from: the `platform` tab is
 *   offered to everyone (unlike the `storage`/`weather` tabs, which are built
 *   only when `canManageStorage`), and `AccountSettingsPage` derives its own
 *   `isPlatformAdmin` by *probing* the three admin endpoints and catching the
 *   403 — so a non-admin who opens `/settings#platform` still gets the tab, with
 *   empty cards behind it. That is the same defect on the same axis at the tab
 *   level, and it is deliberately **not** fixed here: it belongs to the page, not
 *   to the router. Recorded in the #1336 pull request as a follow-up.
 * - `stammdaten/species/:key` (reference-image curation) and
 *   `pflanzenschutz/pests/:key` (the pest gallery's curation controls) — read
 *   pages with an admin-only panel inside, already gated on `usePlatformAdmin()`
 *   at the component. Same shape as the action-gated bucket on the other axis.
 *
 * ## What a refused member sees, and why it differs from #1261
 *
 * `<RequireRole>` restricts but never replaces, because the API leaves the reads
 * of every domain-guarded route open (REQ-049 §2.3) and blocking would remove
 * access the server grants. That reasoning **does not transfer here** — checked
 * rather than assumed: `GET /admin/platform/tenants` and `GET /admin/platform/users`
 * carry `require_platform_admin` exactly like the writes beside them. A banner
 * over the page would sit above nothing, and today's behaviour is worse than
 * nothing: `AdminEditTenantPage` swallows the 403 and renders
 * `pages.admin.tenantNotFound`, telling a member the tenant does not exist when
 * it does and they merely may not see it. So refusal renders a replacement state
 * — what the page is, that the account lacks the right, and the way back.
 *
 * ## Deliberately not decided here: `admin_scope`
 *
 * `require_admin_scope('management')` on `tenants/settings` and
 * `require_admin_scope('technical')` on `umgebungssteuerung` are a **third**
 * question — additive scopes within a tenant, neither rank nor platform
 * attribute (REQ-049 §2.4). Folding them in would put three meanings in one pass;
 * they keep their current action-level gating and are the next pass.
 */
export const PLATFORM_ADMIN_ROUTES: Readonly<Record<string, PlatformAdminRoute>> = {
  // REQ-024 — the whole page is platform administration: it loads through
  // `GET /admin/platform/tenants`, then edits/deletes the tenant and adds,
  // removes and re-roles its members through the same gated router.
  'admin/tenants/:key': {
    gate: 'GET /api/v1/admin/platform/tenants — require_platform_admin',
  },
  // REQ-023 — the mirror page for a user account: loaded by
  // `GET /admin/platform/users`, with membership management beside it.
  'admin/users/:key': {
    gate: 'GET /api/v1/admin/platform/users — require_platform_admin',
  },
};
