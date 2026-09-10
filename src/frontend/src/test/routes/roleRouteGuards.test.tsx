import { type ReactElement, type ReactNode } from 'react';
import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { router } from '@/routes/AppRoutes';
import {
  ROLE_GUARDED_ROUTES,
  ACTION_GATED_ROUTES,
  UNGATED_ROUTES,
  PLATFORM_ADMIN_ROUTES,
} from '@/routes/roleGuardedRoutes';
import RequireRole from '@/auth/RequireRole';
import PageTitle from '@/components/layout/PageTitle';
import {
  createStoreWithTenantRole,
  createTestStore,
  findElementOfType,
  findFlatRoute,
  flattenRoutes,
  renderWithProviders,
} from '@/test/helpers';
import type { TenantRole } from '@/api/types';

/**
 * #1261 — the router had no role guard at all, so a viewer reached pages whose
 * primary action the API refuses.
 *
 * Every case here is driven by `ROLE_GUARDED_ROUTES` rather than by a list
 * written out in this file. A hand-maintained list of guarded routes is the next
 * thing to drift: adding a sixth guarded route and forgetting to add its test is
 * precisely the shape of #948, so the table is the single input and a new entry
 * is covered the moment it is written.
 *
 * The pairing is asserted against the **constructed route tree** (`router.routes`),
 * not against the source text of `AppRoutes.tsx` — `scripts/check_route_role_guards.py`
 * reads the text. Two measurements of the same rule from two different artefacts,
 * on purpose: a JSX edit that parses but does not produce the wrapper (a comment,
 * a conditional, a moved `</Route>`) is invisible to the text scan and caught here.
 */

const FLAT_ROUTES = flattenRoutes(router.routes);

function routeFor(path: string) {
  return findFlatRoute(FLAT_ROUTES, path);
}

/**
 * The `min` a route's element declares, or `null` when it carries no guard.
 *
 * Searches the whole element subtree rather than the outermost tag, so a guard
 * nested under another wrapper still counts — the hole the #1336 review found in
 * the static checker's text scan, mirrored here on purpose.
 */
function declaredMinimum(element: ReactNode): TenantRole | null {
  const guard = findElementOfType(element, RequireRole);
  if (!guard) return null;
  return (guard as ReactElement<{ min: TenantRole }>).props.min;
}

const GUARDED_ENTRIES = Object.entries(ROLE_GUARDED_ROUTES);

describe('AppRoutes — role-guard placement (#1261)', () => {
  it.each(GUARDED_ENTRIES)(
    'wraps "%s" in <RequireRole> with the minimum the table declares',
    (path, rule) => {
      expect(declaredMinimum(routeFor(path).element)).toBe(rule.min);
    },
  );

  it('carries no <RequireRole> on a route the table does not declare', () => {
    // The other direction. Without it a guard could be added to a route whose
    // backend gate nobody checked, which is how a *stricter*-than-the-API guard
    // (a usability bug) gets shipped unnoticed.
    const wrapped = FLAT_ROUTES.filter((r) => declaredMinimum(r.element) !== null).map(
      (r) => r.path,
    );
    expect(wrapped.sort()).toEqual(Object.keys(ROLE_GUARDED_ROUTES).sort());
  });

  it('decides every registered route, and decides none of them twice', () => {
    // A route that reaches a gated endpoint and nobody looked at is the #948
    // shape one level up, so the table has to cover the router — not just the
    // guarded part of it.
    const decided = [
      ...Object.keys(ROLE_GUARDED_ROUTES),
      // The second axis (#1336) is a fourth bucket of the same partition: every
      // route carries exactly one decision, whichever question it answers.
      ...Object.keys(PLATFORM_ADMIN_ROUTES),
      ...ACTION_GATED_ROUTES,
      ...UNGATED_ROUTES,
    ];
    expect(new Set(decided).size).toBe(decided.length);

    const undecided = FLAT_ROUTES.map((r) => r.path).filter((p) => !decided.includes(p));
    expect(undecided).toEqual([]);

    // The opposite direction — a bucket entry naming a route that no longer
    // exists — is asserted by `scripts/check_route_role_guards.py`, which reads
    // the router *source*. It cannot be asserted here: several routes are
    // mounted only when `isLightMode` is false (REQ-027), so the constructed
    // route tree is a subset of the declared one in a light-mode build, and an
    // equality assertion here would go red for the wrong reason.
  });
});

/**
 * Behaviour of the guard itself, driven by the same table.
 *
 * The probe stands in for a guarded page: a `PageTitle` whose header action is
 * the gated write (which is the criterion for entering the table at all) plus a
 * body that every member may read.
 */
function Probe() {
  return (
    <>
      <PageTitle
        title="Probe"
        action={<button data-testid="probe-primary-action">Anlegen</button>}
      />
      <div data-testid="probe-read-surface">Verlauf</div>
    </>
  );
}

const ALL_ROLES: TenantRole[] = ['viewer', 'grower', 'lead'];

describe('RequireRole — what a member of each role gets', () => {
  it.each(GUARDED_ENTRIES)('refuses the primary action of "%s" to a viewer', (_path, rule) => {
    renderWithProviders(
      <RequireRole min={rule.min}>
        <Probe />
      </RequireRole>,
      { store: createStoreWithTenantRole('viewer') },
    );

    expect(screen.getByTestId('role-restriction-notice')).toBeInTheDocument();
    expect(screen.queryByTestId('probe-primary-action')).not.toBeInTheDocument();
    // The half that must survive: reads are open to every member (REQ-049 §2.3),
    // so restricting must not cost the page.
    expect(screen.getByTestId('probe-read-surface')).toBeInTheDocument();
  });

  it.each(
    GUARDED_ENTRIES.flatMap(([path, rule]) =>
      ALL_ROLES.filter((role) => role !== 'viewer').map(
        (role) => [path, rule.min, role] as const,
      ),
    ),
  )('lets a %s reach "%s" untouched (min %s)', (_path, min, role) => {
    // The regression this exists to prevent is locking out legitimate users,
    // which is worse than the bug being fixed. Every role at or above the
    // declared minimum must see exactly what it saw before the guard existed.
    renderWithProviders(
      <RequireRole min={min}>
        <Probe />
      </RequireRole>,
      { store: createStoreWithTenantRole(role) },
    );

    expect(screen.queryByTestId('role-restriction-notice')).not.toBeInTheDocument();
    expect(screen.getByTestId('probe-primary-action')).toBeInTheDocument();
  });

  it('does not restrict while no active tenant is resolved yet', () => {
    // The auth-bootstrap and stale-slug-recovery window (#1091 A-4). Reading
    // "cannot prove the role" as a refusal would flash the banner at every
    // member on every reload — and in light mode (REQ-027), where the single
    // seeded operator is a lead, it would flash before the tenant loads.
    renderWithProviders(
      <RequireRole min="grower">
        <Probe />
      </RequireRole>,
      { store: createTestStore() },
    );

    expect(screen.queryByTestId('role-restriction-notice')).not.toBeInTheDocument();
    expect(screen.getByTestId('probe-primary-action')).toBeInTheDocument();
  });

  it('needs lead for a lead minimum — a grower is restricted too', () => {
    // No route declares `lead` today. Asserting the rank comparison rather than
    // only the shipped configuration keeps the guard honest the day one does:
    // a predicate hard-wired to "viewer" would pass every test above.
    renderWithProviders(
      <RequireRole min="lead">
        <Probe />
      </RequireRole>,
      { store: createStoreWithTenantRole('grower') },
    );

    expect(screen.getByTestId('role-restriction-notice')).toBeInTheDocument();
    expect(screen.queryByTestId('probe-primary-action')).not.toBeInTheDocument();
  });

  it('leaves the primary action in place without the wrapper — negative control', () => {
    // The falsification, asserting the *same* expression as the case above with
    // the *same* viewer store: removing the guard must let the viewer through
    // again. Without this, a `PageTitle` that dropped its action for an
    // unrelated reason would satisfy every assertion above while the guard did
    // nothing at all.
    renderWithProviders(<Probe />, { store: createStoreWithTenantRole('viewer') });

    expect(screen.getByTestId('probe-primary-action')).toBeInTheDocument();
    expect(screen.queryByTestId('role-restriction-notice')).not.toBeInTheDocument();
  });
});
