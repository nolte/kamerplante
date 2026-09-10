import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import PageTitle from '@/components/layout/PageTitle';
import { usePlatformAdmin } from '@/hooks/usePlatformAdmin';
import { useAppSelector } from '@/store/hooks';

interface RequirePlatformAdminProps {
  children: ReactNode;
}

/**
 * Route-level **platform-admin** guard (#1336, REQ-049 §2.4).
 *
 * Wraps a route whose page is a platform-administration surface — every request
 * it makes is gated by `require_platform_admin`, so a member without that
 * attribute is refused the whole resource, not merely its actions. Before this
 * existed the router consulted the attribute nowhere: any tenant member could
 * open `/admin/tenants/:key`, watch the load fail, and be told
 * *"tenant not found"* — a false explanation, since the tenant exists and the
 * server answered 403 (measured, see `roleGuardedRoutes.ts`).
 *
 * ## Why this is a second component and not a second prop on `<RequireRole>`
 *
 * REQ-049 §2.4 keeps the two axes disjoint, and the backend agrees: neither
 * `require_tenant_role` nor `require_permission` consults `is_platform_admin`,
 * and `require_platform_admin` consults no domain role. They are not a
 * hierarchy, so there is no single rank to compare and no way for one component
 * to answer both questions without meaning two things at once. Each component
 * therefore answers exactly one, and a route needing both would nest them.
 *
 * ## Why refusal replaces the page here, where `<RequireRole>` only restricts
 *
 * That difference is measured, not preferred. `<RequireRole>` leaves the page
 * standing because the API leaves its *reads* open to every member (REQ-049
 * §2.3) — blocking there would take away access the server grants. On these
 * routes it grants nothing: `GET /admin/platform/tenants` and
 * `GET /admin/platform/users` are `require_platform_admin` just like the writes
 * beside them, so a refused member has nothing to read. A banner over an empty
 * page would claim there is content behind it. The honest answer is to say what
 * is missing and offer the way back.
 *
 * ## "Not loaded yet" is not a refusal
 *
 * The predicate is *"a profile IS loaded and it is not a platform admin"*, the
 * same reading `<RequireRole>` and `useCanCreateCatalogEntry` apply to their
 * inputs. `usePlatformAdmin` reads `auth.user?.is_platform_admin ?? false`, so
 * during the auth bootstrap — before `/users/me` has answered — it reports
 * `false` for an admin too; treating that as a refusal would flash this notice
 * at the very users the page is for. `ProtectedRoute` already holds the subtree
 * back until the bootstrap concludes, which makes this the second line rather
 * than the first, and a defensive one is cheap.
 *
 * **This is a UX consequence of the backend gate, never a security control.**
 * `require_platform_admin` refuses a non-admin whatever this component renders,
 * and both sides read the same value: `/users/me` reports the very
 * `app.common.auth.is_platform_admin` the dependency raises on.
 */
export default function RequirePlatformAdmin({ children }: RequirePlatformAdminProps) {
  const { t } = useTranslation();
  const isPlatformAdmin = usePlatformAdmin();
  const profileKnown = useAppSelector((s) => s.auth.user !== null);

  if (isPlatformAdmin || !profileKnown) {
    return <>{children}</>;
  }

  return (
    <Box data-testid="platform-admin-required-page">
      <PageTitle title={t('platformAdminGuard.title')} />
      <Alert severity="info" data-testid="platform-admin-required-notice">
        <AlertTitle>{t('platformAdminGuard.noticeTitle')}</AlertTitle>
        {t('platformAdminGuard.description')}
      </Alert>
      <Button
        component={RouterLink}
        to="/dashboard"
        variant="contained"
        sx={{ mt: 3 }}
        data-testid="platform-admin-required-back-button"
      >
        {t('platformAdminGuard.backToDashboard')}
      </Button>
    </Box>
  );
}
