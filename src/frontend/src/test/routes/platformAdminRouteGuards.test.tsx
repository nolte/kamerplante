import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { router } from '@/routes/AppRoutes';
import { PLATFORM_ADMIN_ROUTES } from '@/routes/roleGuardedRoutes';
import RequirePlatformAdmin from '@/auth/RequirePlatformAdmin';
import RequireRole from '@/auth/RequireRole';
import { fetchProfile } from '@/store/slices/authSlice';
import {
  createStoreWithTenantRole,
  createTestStore,
  findElementOfType,
  findFlatRoute,
  flattenRoutes,
  renderWithProviders,
} from '@/test/helpers';

/**
 * #1336 — the router consulted the **platform-admin** attribute nowhere, so any
 * tenant member could open `/admin/tenants/:key` and `/admin/users/:key`. The API
 * answers 403 there, including on the two reads the pages load with, and
 * `AdminEditTenantPage` reports every failure as "tenant not found" — so the
 * refusal arrived as a false explanation for a tenant that exists.
 *
 * Same defect class as #1261, **different axis**: REQ-049 §2.4 keeps the domain
 * rank and the platform attribute disjoint, so this is a second wrapper reading a
 * second table, not a second mode of the first one. The cases below assert that
 * separation directly (a tenant `lead` is refused just like a `viewer`), because
 * "strictest domain role ⇒ admin" is the mistake the split exists to prevent.
 *
 * Every case is driven by `PLATFORM_ADMIN_ROUTES`, never by a list written out
 * here: a hand-kept list is the next thing to drift (#948), and the last
 * assertion closes the remaining hole by requiring the table to cover **every**
 * `admin/*` route the router registers, not the two that were reported.
 */

const FLAT_ROUTES = flattenRoutes(router.routes);

function routeFor(path: string) {
  return findFlatRoute(FLAT_ROUTES, path);
}

/** Whether the route's element subtree carries the platform-admin wrapper. */
function isPlatformGuarded(element: ReactNode): boolean {
  return findElementOfType(element, RequirePlatformAdmin) !== null;
}

const PLATFORM_ENTRIES = Object.entries(PLATFORM_ADMIN_ROUTES);

describe('AppRoutes — platform-admin guard placement (#1336)', () => {
  it.each(PLATFORM_ENTRIES)('wraps "%s" in <RequirePlatformAdmin>', (path) => {
    // The structural half, asserted against the *constructed* route tree while
    // `scripts/check_route_role_guards.py` asserts the same rule against the
    // router source. A JSX edit that parses but does not produce the wrapper (a
    // comment, a conditional, a moved `</Route>`) is invisible to the text scan.
    expect(isPlatformGuarded(routeFor(path).element)).toBe(true);
  });

  it('wraps no route the table does not declare', () => {
    const wrapped = FLAT_ROUTES.filter((r) => isPlatformGuarded(r.element)).map((r) => r.path);
    expect(wrapped.sort()).toEqual(Object.keys(PLATFORM_ADMIN_ROUTES).sort());
  });

  it('covers every admin/* route the router registers', () => {
    // The inventory rule. #1261's pull request found these two by surveying the
    // router; nothing then stopped a third from being added undecided, which is
    // exactly how #948 kept two of four siblings open for months.
    const adminRoutes = FLAT_ROUTES.map((r) => r.path).filter((p) => p.startsWith('admin/'));
    expect(adminRoutes.length).toBeGreaterThan(0);
    expect(adminRoutes.sort()).toEqual(Object.keys(PLATFORM_ADMIN_ROUTES).sort());
  });

  it('records the backend gate it mirrors for every entry', () => {
    // The check the script cannot make: whether a decision is *correct* is read
    // by a human off the recorded gate, so an entry naming none is unreviewable.
    for (const [, rule] of PLATFORM_ENTRIES) {
      expect(rule.gate).toMatch(/require_platform_admin/);
    }
  });

  it('does not double-guard: no admin route carries <RequireRole> anywhere inside', () => {
    // The axes are disjoint (REQ-049 §2.4), and the decision table is a
    // partition — two entries for one route are `decided-twice` in
    // `check_route_role_guards.py`. The search walks the whole element subtree
    // rather than the outermost tag: the script's text scan read only the outer
    // wrapper at first and reported a nested pair as clean, so a check here that
    // looked only at `element.type` would repeat that hole in the second
    // measurement, which exists precisely to not repeat it.
    const roleWrapped = FLAT_ROUTES.filter(
      (r) => findElementOfType(r.element, RequireRole) !== null,
    ).map((r) => r.path);
    expect(roleWrapped.filter((p) => p in PLATFORM_ADMIN_ROUTES)).toEqual([]);
  });
});

/** Store with a loaded profile whose platform-admin attribute is `isAdmin`. */
function storeForProfile(isAdmin: boolean) {
  return createTestStore({
    auth: {
      user: { key: 'user-1', email: 'member@example.test', is_platform_admin: isAdmin },
      isAuthenticated: true,
      isLoading: false,
      initialized: true,
    },
  });
}

function Probe() {
  return <div data-testid="admin-probe-content">Mandantenverwaltung</div>;
}

describe('RequirePlatformAdmin — what each caller gets', () => {
  it('replaces the page for a member who is not a platform admin', () => {
    renderWithProviders(
      <RequirePlatformAdmin>
        <Probe />
      </RequirePlatformAdmin>,
      { store: storeForProfile(false) },
    );

    expect(screen.getByTestId('platform-admin-required-page')).toBeInTheDocument();
    expect(screen.getByTestId('platform-admin-required-notice')).toBeInTheDocument();
    // Replacement, not restriction — deliberately unlike <RequireRole>: the API
    // refuses the reads too, so leaving the page standing would promise content
    // that cannot load.
    expect(screen.queryByTestId('admin-probe-content')).not.toBeInTheDocument();
  });

  it('offers the way back instead of leaving a dead end', () => {
    renderWithProviders(
      <RequirePlatformAdmin>
        <Probe />
      </RequirePlatformAdmin>,
      { store: storeForProfile(false) },
    );

    const back = screen.getByTestId('platform-admin-required-back-button');
    expect(back).toHaveAttribute('href', '/dashboard');
  });

  it('lets a platform admin through untouched', () => {
    // The regression that would be worse than the bug: locking out the users the
    // page exists for.
    renderWithProviders(
      <RequirePlatformAdmin>
        <Probe />
      </RequirePlatformAdmin>,
      { store: storeForProfile(true) },
    );

    expect(screen.getByTestId('admin-probe-content')).toBeInTheDocument();
    expect(screen.queryByTestId('platform-admin-required-page')).not.toBeInTheDocument();
  });

  it('does not refuse before the bootstrap has run at all', () => {
    // `usePlatformAdmin` reports `false` for an admin too until `/users/me` has
    // answered. Reading that as a refusal would flash this notice at the very
    // users the page is for. Nobody is signed in here, so the question is not
    // this guard's — `ProtectedRoute` owns it.
    renderWithProviders(
      <RequirePlatformAdmin>
        <Probe />
      </RequirePlatformAdmin>,
      { store: createTestStore() },
    );

    expect(screen.getByTestId('admin-probe-content')).toBeInTheDocument();
    expect(screen.queryByTestId('platform-admin-required-page')).not.toBeInTheDocument();
  });

  it('holds the real bootstrap window on a skeleton — neither answer yet', () => {
    // The window `ProtectedRoute` does not cover, and the case the store above
    // does *not* reach: the JWT bootstrap resolves `refreshAccessToken` first,
    // which sets `initialized` AND `isAuthenticated` (authSlice), and only then
    // awaits `fetchProfile` (AuthProvider.initAuth). `ProtectedRoute` gates on
    // `initialized` alone, so passing children through here means a plain member
    // reloading /admin/tenants/<key> mounts the page, fires `fetchAdminTenants()`
    // and reads "Mandant nicht gefunden" until the profile arrives — the exact
    // sequence this guard exists to end. Refusing instead would flash the notice
    // at an admin, so the honest answer is "not known yet".
    renderWithProviders(
      <RequirePlatformAdmin>
        <Probe />
      </RequirePlatformAdmin>,
      {
        store: createTestStore({
          auth: { user: null, isAuthenticated: true, isLoading: true, initialized: true },
        }),
      },
    );

    expect(screen.getByTestId('loading-skeleton')).toBeInTheDocument();
    expect(screen.queryByTestId('admin-probe-content')).not.toBeInTheDocument();
    expect(screen.queryByTestId('platform-admin-required-page')).not.toBeInTheDocument();
  });

  it('cannot hang on the skeleton when the profile fetch fails', () => {
    // `fetchProfile.rejected` clears `isAuthenticated` and `user` together, so
    // the failure state is not the waiting state: it falls through to the
    // pass-through arm and lands in `ProtectedRoute`'s redirect to /login.
    // Without this, "wait for the profile" would be a way to strand a user on a
    // skeleton forever.
    const store = createTestStore({
      auth: { user: null, isAuthenticated: true, isLoading: true, initialized: true },
    });
    store.dispatch({ type: fetchProfile.rejected.type, error: { message: 'boom' } });

    renderWithProviders(
      <RequirePlatformAdmin>
        <Probe />
      </RequirePlatformAdmin>,
      { store },
    );

    expect(screen.queryByTestId('loading-skeleton')).not.toBeInTheDocument();
    expect(screen.getByTestId('admin-probe-content')).toBeInTheDocument();
  });

  it.each(['viewer', 'grower', 'lead'] as const)(
    'refuses a tenant %s who is not a platform admin',
    (role) => {
      // The axes are not a hierarchy: the top domain role does not imply the
      // platform attribute, and `require_platform_admin` consults no role at all.
      // A predicate that let a lead through would be looser than the API.
      const store = createStoreWithTenantRole(role);
      store.dispatch({
        type: fetchProfile.fulfilled.type,
        payload: { key: 'user-1', email: 'member@example.test', is_platform_admin: false },
      });

      renderWithProviders(
        <RequirePlatformAdmin>
          <Probe />
        </RequirePlatformAdmin>,
        { store },
      );

      expect(screen.getByTestId('platform-admin-required-page')).toBeInTheDocument();
      expect(screen.queryByTestId('admin-probe-content')).not.toBeInTheDocument();
    },
  );

  it('renders the probe without the wrapper — negative control', () => {
    // The falsification, asserting the *same* expression with the *same* store:
    // without the guard the refused member does reach the content. Otherwise
    // "the content is absent" would also be satisfied by a probe that never
    // rendered at all.
    renderWithProviders(<Probe />, { store: storeForProfile(false) });

    expect(screen.getByTestId('admin-probe-content')).toBeInTheDocument();
    expect(screen.queryByTestId('platform-admin-required-page')).not.toBeInTheDocument();
  });
});
