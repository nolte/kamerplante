import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ApiError } from '@/api/errors';
import { createTestStore, renderWithProviders } from '@/test/helpers';

/**
 * #1390 — `AdminEditTenantPage` and `AdminEditUserPage` load with a `.then()` and
 * no `.catch()`. Every rejection — 403, 500, a dropped connection, a rate limit —
 * left the record at `null`, and the render fell through to
 * `pages.admin.tenantNotFound`: **"Mandant nicht gefunden."** for a tenant that
 * exists and is untouched. The rejection was unhandled besides, so it surfaced as
 * an unhandled promise rejection rather than anywhere anyone could see it.
 *
 * `<RequirePlatformAdmin>` (#1336) closed the 403-for-a-non-admin path by not
 * mounting the page for those callers. It does nothing for the rest, which is why
 * this file drives a **platform admin** through failures the guard cannot prevent.
 *
 * Both pages are the same shape and are asserted together on purpose: fixing one
 * and leaving the other is the #948 sibling drift this repository keeps paying
 * for, and the pair is small enough that a table-driven test costs nothing.
 */

// `renderWithProviders` builds its own router at path `*`, so `useParams()` would
// hand the page no `key` at all. Substituting the hook is smaller than standing up
// a second router inside the first one, which React Router v7 does not allow.
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual<typeof import('react-router-dom')>('react-router-dom')),
  useParams: () => ({ key: 'the-key' }),
}));

vi.mock('@/api/endpoints/adminPlatform', () => ({
  fetchAdminTenants: vi.fn(),
  fetchAdminUsers: vi.fn(),
  fetchTenantMembers: vi.fn().mockResolvedValue([]),
  fetchUserMemberships: vi.fn().mockResolvedValue([]),
  updateAdminTenant: vi.fn(),
  updateAdminUser: vi.fn(),
  deleteAdminTenant: vi.fn(),
  deleteAdminUser: vi.fn(),
  addTenantMember: vi.fn(),
  removeTenantMember: vi.fn(),
  changeTenantMemberRole: vi.fn(),
  addUserToTenant: vi.fn(),
  removeUserFromTenant: vi.fn(),
  changeUserMembershipRole: vi.fn(),
}));

const admin = await import('@/api/endpoints/adminPlatform');

const PAGES = [
  {
    name: 'AdminEditTenantPage',
    load: () => import('@/pages/admin/AdminEditTenantPage'),
    fetcher: () => admin.fetchAdminTenants as ReturnType<typeof vi.fn>,
    notFoundKey: 'pages.admin.tenantNotFound',
    record: { key: 'the-key', name: 'Mein Garten', description: '', is_active: true },
  },
  {
    name: 'AdminEditUserPage',
    load: () => import('@/pages/admin/AdminEditUserPage'),
    fetcher: () => admin.fetchAdminUsers as ReturnType<typeof vi.fn>,
    notFoundKey: 'pages.admin.userNotFound',
    record: { key: 'the-key', display_name: 'Jemand', email: 'a@b.c', is_active: true, email_verified: true },
  },
] as const;

function apiError(statusCode: number) {
  return new ApiError(
    {
      error_id: 'err_1',
      error_code: 'INTERNAL_ERROR',
      message: 'boom',
      details: [],
      timestamp: '',
      path: '/x',
      method: 'GET',
    },
    statusCode,
  );
}

async function renderPage(page: (typeof PAGES)[number]) {
  const { default: Page } = await page.load();
  return renderWithProviders(<Page />, { store: createTestStore() });
}

describe.each(PAGES)('$name load failure', (page) => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => cleanup());

  it('does not claim the record is missing when the request fails', async () => {
    page.fetcher().mockRejectedValue(apiError(500));

    await renderPage(page);

    await waitFor(() => {
      expect(screen.queryByText(/nicht gefunden|not found/i)).not.toBeInTheDocument();
    });
  });

  it.each([403, 500, 429])('shows an error state for %i', async (status) => {
    page.fetcher().mockRejectedValue(apiError(status));

    await renderPage(page);

    // `ErrorPage` renders a retry control; the not-found alert does not. Keyed on
    // the testid rather than the label, which is translated.
    await waitFor(() => {
      expect(screen.getByTestId('error-retry')).toBeInTheDocument();
    });
  });

  it('shows an error state when the failure carries no status at all', async () => {
    // A dropped connection is not an ApiError and has no statusCode. It must not
    // fall through to "not found" either — the original defect treated every
    // rejection alike, and a fix keyed only on ApiError would keep half of it.
    page.fetcher().mockRejectedValue(new TypeError('Failed to fetch'));

    await renderPage(page);

    await waitFor(() => {
      expect(screen.getByTestId('error-retry')).toBeInTheDocument();
    });
  });

  it('retries the request when the error state offers it', async () => {
    const fetcher = page.fetcher();
    fetcher.mockRejectedValueOnce(apiError(500)).mockResolvedValueOnce([page.record]);

    await renderPage(page);
    const retry = await screen.findByTestId('error-retry');
    await userEvent.click(retry);

    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  });

  it('still says not found when the list came back and the key is absent', async () => {
    // The control. A page that reports every outcome as an error is as wrong as
    // one that reports every outcome as missing — this is the one case where
    // "not found" is the honest answer.
    page.fetcher().mockResolvedValue([{ ...page.record, key: 'someone-else' }]);

    await renderPage(page);

    await waitFor(() => {
      expect(screen.queryByTestId('error-retry')).not.toBeInTheDocument();
    });
    expect(screen.getByText(/nicht gefunden|not found/i)).toBeInTheDocument();
  });
});
