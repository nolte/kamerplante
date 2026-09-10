import { Children, isValidElement, type ElementType, type ReactElement, type ReactNode } from 'react';
import { render } from '@testing-library/react';
import { Provider } from 'react-redux';
import { combineReducers, configureStore } from '@reduxjs/toolkit';
import { createMemoryRouter, RouterProvider, type RouteObject } from 'react-router-dom';
import { SnackbarProvider } from 'notistack';
import { ThemeContextProvider } from '@/theme';
import uiReducer from '@/store/slices/uiSlice';
import botanicalFamiliesReducer from '@/store/slices/botanicalFamiliesSlice';
import speciesReducer from '@/store/slices/speciesSlice';
import sitesReducer from '@/store/slices/sitesSlice';
import substratesReducer from '@/store/slices/substratesSlice';
import plantInstancesReducer from '@/store/slices/plantInstancesSlice';
import userPreferencesReducer from '@/store/slices/userPreferencesSlice';
import authReducer from '@/store/slices/authSlice';
import identificationReducer from '@/store/slices/identificationSlice';
import aiStatusReducer from '@/store/slices/aiStatusSlice';
import pestDetectionReducer from '@/store/slices/pestDetectionSlice';
import ipmReducer from '@/store/slices/ipmSlice';
import tenantsReducer from '@/store/slices/tenantSlice';
import successionPlansReducer from '@/store/slices/successionPlansSlice';
import overwinteringProfilesReducer from '@/store/slices/overwinteringProfilesSlice';
import seasonReducer from '@/store/slices/seasonSlice';
import dashboardReducer from '@/store/slices/dashboardSlice';
import plantingRunsReducer from '@/store/slices/plantingRunsSlice';
import tasksReducer from '@/store/slices/tasksSlice';
import harvestReducer from '@/store/slices/harvestSlice';
import postHarvestReducer from '@/store/slices/postHarvestSlice';
import careRemindersReducer from '@/store/slices/careRemindersSlice';
import wateringLogsReducer from '@/store/slices/wateringLogsSlice';
import fertilizersReducer from '@/store/slices/fertilizersSlice';

const rootReducer = combineReducers({
  ui: uiReducer,
  botanicalFamilies: botanicalFamiliesReducer,
  species: speciesReducer,
  sites: sitesReducer,
  substrates: substratesReducer,
  plantInstances: plantInstancesReducer,
  userPreferences: userPreferencesReducer,
  auth: authReducer,
  identification: identificationReducer,
  aiStatus: aiStatusReducer,
  pestDetection: pestDetectionReducer,
  ipm: ipmReducer,
  tenants: tenantsReducer,
  successionPlans: successionPlansReducer,
  overwinteringProfiles: overwinteringProfilesReducer,
  season: seasonReducer,
  dashboard: dashboardReducer,
  plantingRuns: plantingRunsReducer,
  tasks: tasksReducer,
  harvest: harvestReducer,
  postHarvest: postHarvestReducer,
  careReminders: careRemindersReducer,
  wateringLogs: wateringLogsReducer,
  fertilizers: fertilizersReducer,
});

// Loosely-typed preloaded state: only the slices a given test cares about need
// to be supplied. configureStore fills the rest from each reducer's initial state.
type PreloadedState = Record<string, unknown>;

export function createTestStore(preloadedState?: PreloadedState) {
  return configureStore({
    reducer: rootReducer,
    preloadedState: preloadedState as never,
  });
}

export type TestStore = ReturnType<typeof createTestStore>;

type ExpertiseLevel = 'beginner' | 'intermediate' | 'expert';

/**
 * Store seeded with a loaded user-preference experience level. Components that
 * gate fields behind {@link useExpertiseLevel} (ExpertiseFieldWrapper) show the
 * intermediate/expert fields only when a preference is actually loaded.
 */
export function createStoreWithExpertise(
  level: ExpertiseLevel,
  // Issue #587: sensor/monitoring surfaces (e.g. the monitoring widget category)
  // only appear when smart home is on. Defaults to false (pre-#587 behaviour).
  smartHomeEnabled = false,
): TestStore {
  return createTestStore({
    userPreferences: {
      preferences: {
        key: 'pref-1',
        user_key: 'user-1',
        experience_level: level,
        onboarding_completed: true,
        locale: 'de',
        theme: 'light',
        watering_can_liters: 5,
        smart_home_enabled: smartHomeEnabled,
        module_visibility: {},
      },
      loading: false,
      error: null,
    },
  });
}

type ModuleVisibilityState = 'enabled' | 'disabled';

/**
 * Store seeded with a loaded experience level plus REQ-042 module-visibility
 * overrides — for components/hooks that combine both signals.
 */
export function createStoreWithModuleOverrides(
  level: ExpertiseLevel,
  overrides: Record<string, ModuleVisibilityState>,
  // Issue #587: smart-home-gated modules (e.g. automation) only appear when this
  // is true. Defaults to false to preserve the pre-#587 behaviour of callers.
  smartHomeEnabled = false,
): TestStore {
  return createTestStore({
    userPreferences: {
      preferences: {
        key: 'pref-1',
        user_key: 'user-1',
        experience_level: level,
        onboarding_completed: true,
        locale: 'de',
        theme: 'light',
        watering_can_liters: 5,
        smart_home_enabled: smartHomeEnabled,
        module_visibility: overrides,
      },
      loading: false,
      error: null,
    },
  });
}

/**
 * Store seeded with an active tenant in which the acting user holds `role`
 * (REQ-049 §2.3) — what `<RequireRole>` and `useTenantPermissions` decide on.
 *
 * `activeTenant: null` is a *different* input, not "role viewer": it is the
 * auth-bootstrap / stale-slug-recovery window, in which the guard must NOT
 * restrict. Pass `createTestStore()` for that case rather than a role here.
 */
export function createStoreWithTenantRole(
  role: 'viewer' | 'grower' | 'lead',
  adminScopes: readonly string[] = [],
): TestStore {
  return createTestStore({
    tenants: {
      activeTenant: {
        key: 'tenant-1',
        name: 'Testgarten',
        slug: 'testgarten',
        tenant_type: 'organization',
        description: null,
        role,
        admin_scopes: [...adminScopes],
        avatar_url: null,
        owner_key: 'user-1',
        max_members: 50,
        created_at: null,
        updated_at: null,
      },
      myTenants: [],
      isLoading: false,
      error: null,
    },
  });
}

/**
 * Store seeded with the smart-home toggle enabled (issue #587). Sensor/actuator
 * surfaces are hidden until `smart_home_enabled` is true, so tests that exercise
 * that UI need this store. Experience level is left unknown (matches the null
 * default), so expertise-gated behaviour is unchanged.
 */
export function createStoreWithSmartHome(enabled = true): TestStore {
  return createTestStore({
    userPreferences: {
      preferences: {
        smart_home_enabled: enabled,
      },
      loading: false,
      error: null,
    },
  });
}

export function renderWithProviders(
  ui: ReactElement,
  { store = createTestStore(), route = '/' }: { store?: TestStore; route?: string } = {},
) {
  const router = createMemoryRouter(
    [{ path: '*', element: ui }],
    { initialEntries: [route] },
  );
  return {
    store,
    ...render(
      <Provider store={store}>
        <ThemeContextProvider>
          <SnackbarProvider>
            <RouterProvider router={router} />
          </SnackbarProvider>
        </ThemeContextProvider>
      </Provider>,
    ),
  };
}

/** One addressable route of the constructed router tree. */
export interface FlatRoute {
  path: string;
  element: ReactNode;
}

/**
 * Every addressable route of a router tree, depth-first (#1261, #1336).
 *
 * Lives here rather than in each route test because two suites assert route
 * decisions from two tables, and a second copy of the traversal is the thing
 * that drifts: the platform-admin suite would keep walking a tree the
 * domain-role suite had learned to walk differently.
 */
export function flattenRoutes(routes: RouteObject[]): FlatRoute[] {
  const flat: FlatRoute[] = [];
  for (const route of routes) {
    if (route.path) flat.push({ path: route.path, element: route.element });
    if (route.children) flat.push(...flattenRoutes(route.children));
  }
  return flat;
}

/** The flattened route registered at `path`, or a failure naming it. */
export function findFlatRoute(routes: FlatRoute[], path: string): FlatRoute {
  const match = routes.find((route) => route.path === path);
  if (!match) throw new Error(`Route "${path}" is not registered in AppRoutes.tsx`);
  return match;
}

/**
 * The first element of type `type` anywhere in `node`'s subtree, or `null`.
 *
 * Deliberately **not** "is the outermost element this type": a route may nest
 * guards (`<RequirePlatformAdmin><RequireRole …>`), and a check that read only
 * the outer one reported the inner as absent — measured on
 * `scripts/check_route_role_guards.py`, whose text scan had the same hole and
 * passed a route wrapped in one axis while the table declared the other. Both
 * measurements of that rule now walk the whole subtree.
 */
export function findElementOfType(node: ReactNode, type: ElementType): ReactElement | null {
  if (!isValidElement(node)) return null;
  if (node.type === type) return node;
  const { children } = node.props as { children?: ReactNode };
  for (const child of Children.toArray(children)) {
    const found = findElementOfType(child, type);
    if (found) return found;
  }
  return null;
}
