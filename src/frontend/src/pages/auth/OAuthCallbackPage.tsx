import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import { useTranslation } from 'react-i18next';
import { useAppDispatch } from '@/store/hooks';
import { setAccessToken, fetchProfile, refreshAccessToken } from '@/store/slices/authSlice';

/**
 * AP-7 (FE-S1/S3): allowed OAuth error codes redirected by the backend, mapped
 * to i18n keys. The `error` query parameter is NEVER rendered raw — unknown
 * values fall back to the generic message so an attacker cannot inject
 * arbitrary "official" text (phishing) via a crafted callback URL.
 */
const OAUTH_ERROR_KEYS: Record<string, string> = {
  access_denied: 'pages.auth.oauthErrors.accessDenied',
  invalid_state: 'pages.auth.oauthErrors.invalidState',
  provider_error: 'pages.auth.oauthErrors.providerError',
  account_disabled: 'pages.auth.oauthErrors.accountDisabled',
  // #1403: the address matches a local account and one side is unverified. Its
  // own key because the generic `providerError` is wrong in both halves here —
  // the provider reported nothing wrong, and "try again later" cannot help.
  link_requires_password: 'pages.auth.oauthErrors.linkRequiresPassword',
};

/**
 * OAuth login completion page.
 *
 * AP-7 (FE-S1): the access token is NEVER read from the URL (neither query nor
 * fragment). The backend has already set the HttpOnly refresh cookie in the
 * callback redirect, so this page finishes the login exactly like the app-mount
 * bootstrap (`AuthProvider.initAuth`): trigger the cookie-based refresh, then
 * load the profile. A token injected via `?access_token=...` is ignored.
 */
export default function OAuthCallbackPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [searchParams] = useSearchParams();
  const [errorKey, setErrorKey] = useState<string | null>(null);

  useEffect(() => {
    const errorParam = searchParams.get('error');
    if (errorParam) {
      setErrorKey(OAUTH_ERROR_KEYS[errorParam] ?? 'pages.auth.oauthErrors.generic');
      return;
    }

    let cancelled = false;
    dispatch(refreshAccessToken())
      .unwrap()
      .then((result) => {
        if (cancelled) return undefined;
        dispatch(setAccessToken(result.access_token));
        return dispatch(fetchProfile()).unwrap();
      })
      .then(() => {
        if (!cancelled) navigate('/dashboard', { replace: true });
      })
      .catch(() => {
        if (!cancelled) setErrorKey('pages.auth.oauthErrors.sessionFailed');
      });

    return () => {
      cancelled = true;
    };
  }, [searchParams, dispatch, navigate]);

  if (errorKey) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '80vh',
          gap: 2,
          px: 2,
        }}
      >
        {/* Clear hierarchy: a heading gives the error state its own context,
            instead of an Alert appearing directly on a blank page. */}
        <Typography variant="h5" align="center">
          {t('pages.auth.oauthErrorTitle')}
        </Typography>
        <Alert severity="error" sx={{ maxWidth: 400, width: '100%' }}>
          {t(errorKey)}
        </Alert>
        {/* Focus management: this is the only actionable element on the page and
            the SPA navigation does not otherwise move focus here, so autoFocus
            lets keyboard/AT users act immediately without tabbing from the top. */}
        <Button variant="outlined" autoFocus onClick={() => navigate('/login', { replace: true })}>
          {t('pages.auth.backToLogin')}
        </Button>
      </Box>
    );
  }

  return (
    <Box
      role="status"
      aria-live="polite"
      sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', minHeight: '80vh' }}
    >
      <CircularProgress sx={{ mb: 2 }} />
      <Typography>{t('pages.auth.oauthProcessing')}</Typography>
    </Box>
  );
}
