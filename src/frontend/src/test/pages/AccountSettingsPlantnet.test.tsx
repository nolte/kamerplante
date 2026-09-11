import { describe, it, expect, beforeEach, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { renderWithProviders, createTestStore } from '@/test/helpers';
import AccountSettingsPage from '@/pages/auth/AccountSettingsPage';
import type { SystemSettingsResponse } from '@/api/endpoints/adminSettings';

/**
 * REQ-029 Phase 1 — Pl@ntNet section of the admin settings (Integrations tab).
 *
 * Covers: masked key + source badge rendering, save (PUT) and remove (DELETE)
 * flows. The Integrations tab is deep-linked via the URL hash (#ha).
 */

const AUTH_USER = {
  // #1385 put the installation-wide HA and Pl@ntNet cards behind the
  // platform-admin gate, on both sides. These suites drive exactly those
  // cards, so their user is the caller who may reach them. The refusal for
  // everyone else has its own test in AccountSettingsInstanceGating.test.tsx.
  is_platform_admin: true,
  key: 'user-1',
  display_name: 'Tester',
  email: 'tester@example.org',
  locale: 'de',
  timezone: 'Europe/Berlin',
};

function storeWithUser(smartHomeEnabled = false) {
  return createTestStore({
    auth: {
      user: AUTH_USER,
      accessToken: 'tok',
      isAuthenticated: true,
      isLoading: false,
      error: null,
    },
    userPreferences: {
      preferences: {
        key: 'pref-1',
        user_key: 'user-1',
        experience_level: 'expert',
        onboarding_completed: true,
        locale: 'de',
        theme: 'light',
        watering_can_liters: 5,
        smart_home_enabled: smartHomeEnabled,
      },
      loading: false,
      error: null,
    },
  });
}

interface RenderOpts {
  putFails?: boolean;
  testResult?: { success: boolean; message: string };
  testFails?: boolean;
  smartHomeEnabled?: boolean;
}

function renderSettings(systemSettings: SystemSettingsResponse, opts: RenderOpts = {}) {
  let putBody: unknown = null;
  let deleteCalled = false;
  let testBody: unknown = null;

  server.use(
    http.get('/api/v1/admin/settings', () => HttpResponse.json(systemSettings)),
    http.put('/api/v1/admin/settings/plant-identification', async ({ request }) => {
      putBody = await request.json();
      if (opts.putFails) {
        return HttpResponse.json(
          {
            error_id: 'e',
            error_code: 'INTERNAL_ERROR',
            message: 'boom',
            details: [],
            timestamp: '',
            path: '',
            method: 'PUT',
          },
          { status: 500 },
        );
      }
      return HttpResponse.json(systemSettings);
    }),
    http.post('/api/v1/admin/settings/plant-identification/test', async ({ request }) => {
      testBody = await request.json();
      if (opts.testFails) {
        return HttpResponse.error();
      }
      return HttpResponse.json(
        opts.testResult ?? { success: true, message: 'Key works' },
      );
    }),
    http.delete('/api/v1/admin/settings/plant-identification', () => {
      deleteCalled = true;
      return new HttpResponse(null, { status: 204 });
    }),
    http.get('/api/v1/users/me/providers', () => HttpResponse.json([])),
    http.get('/api/v1/users/me/sessions', () => HttpResponse.json([])),
    http.get('/api/v1/auth/api-keys', () => HttpResponse.json([])),
  );

  const result = renderWithProviders(<AccountSettingsPage />, {
    store: storeWithUser(opts.smartHomeEnabled),
    route: '/account#ha',
  });
  return {
    ...result,
    getPutBody: () => putBody,
    getTestBody: () => testBody,
    wasDeleteCalled: () => deleteCalled,
  };
}

const HA_BASE = {
  ha_url: '',
  ha_access_token_masked: '',
  ha_timeout: 10,
  source_ha_url: 'default',
  source_ha_access_token: 'default',
  source_ha_timeout: 'default',
};

// NFR-013 storage block — required on every SystemSettingsResponse mock.
const STORAGE_BASE = {
  backend: 'local-fs',
  local_fs_root: '/data/attachments',
  local_fs_public_base_url: '',
  s3_endpoint_url: '',
  s3_region: '',
  s3_bucket: '',
  s3_use_path_style: false,
  s3_kms_key_id: '',
  s3_force_tls: true,
  s3_access_key_id_configured: false,
  s3_secret_access_key_configured: false,
  source_backend: 'env',
  source_local_fs_root: 'env',
  source_local_fs_public_base_url: 'env',
  source_s3_endpoint_url: 'env',
  source_s3_region: 'env',
  source_s3_bucket: 'env',
  source_s3_use_path_style: 'env',
  source_s3_kms_key_id: 'env',
  source_s3_force_tls: 'env',
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('AccountSettingsPage — Pl@ntNet section', () => {
  it('renders masked key and DB source badge', async () => {
    renderSettings({
      home_assistant: HA_BASE,
      storage: STORAGE_BASE,
      plant_identification: {
        plantnet_api_key_masked: '****2345',
        source_plantnet_api_key: 'db',
      },
    });

    const field = await screen.findByTestId('plantnet-key-field');
    expect(field).toBeInTheDocument();
    // Masked value shown in helper text, never plaintext.
    expect(screen.getByText(/\*\*\*\*2345/)).toBeInTheDocument();
    const chip = screen.getByTestId('plantnet-source-chip');
    expect(chip).toHaveTextContent('Database');
  });

  it('renders env source badge when only env key set', async () => {
    renderSettings({
      home_assistant: HA_BASE,
      storage: STORAGE_BASE,
      plant_identification: {
        plantnet_api_key_masked: '****abcd',
        source_plantnet_api_key: 'env',
      },
    });
    const chip = await screen.findByTestId('plantnet-source-chip');
    expect(chip).toHaveTextContent('Environment variable');
  });

  it('renders "not set" badge when no key configured', async () => {
    renderSettings({
      home_assistant: HA_BASE,
      storage: STORAGE_BASE,
      plant_identification: {
        plantnet_api_key_masked: '',
        source_plantnet_api_key: 'none',
      },
    });
    const chip = await screen.findByTestId('plantnet-source-chip');
    expect(chip).toHaveTextContent('Not set');
  });

  it('saves the entered key via PUT', async () => {
    const user = userEvent.setup();
    const { getPutBody } = renderSettings({
      home_assistant: HA_BASE,
      storage: STORAGE_BASE,
      plant_identification: {
        plantnet_api_key_masked: '',
        source_plantnet_api_key: 'none',
      },
    });

    const field = await screen.findByTestId('plantnet-key-field');
    const input = field.querySelector('input') as HTMLInputElement;
    await user.type(input, 'fresh-plantnet-key');
    await user.click(screen.getByTestId('plantnet-save-btn'));

    await waitFor(() => {
      expect(getPutBody()).toEqual({ plantnet_api_key: 'fresh-plantnet-key' });
    });
    expect(await screen.findByTestId('plantnet-save-success-alert')).toBeInTheDocument();
  });

  it('removes the DB key via DELETE after confirming', async () => {
    const user = userEvent.setup();
    const { wasDeleteCalled } = renderSettings({
      home_assistant: HA_BASE,
      storage: STORAGE_BASE,
      plant_identification: {
        plantnet_api_key_masked: '****2345',
        source_plantnet_api_key: 'db',
      },
    });

    await screen.findByTestId('plantnet-reset-btn');
    await user.click(screen.getByTestId('plantnet-reset-btn'));
    // Confirm in the reset dialog.
    await user.click(await screen.findByRole('button', { name: 'Confirm' }));

    await waitFor(() => {
      expect(wasDeleteCalled()).toBe(true);
    });
  });

  it('disables the reset button when the key is not DB-sourced (env only)', async () => {
    renderSettings({
      home_assistant: HA_BASE,
      storage: STORAGE_BASE,
      plant_identification: {
        plantnet_api_key_masked: '****env',
        source_plantnet_api_key: 'env',
      },
    });
    const resetBtn = await screen.findByTestId('plantnet-reset-btn');
    expect(resetBtn).toBeDisabled();
  });

  it('toggles API-key visibility between password and text', async () => {
    const user = userEvent.setup();
    renderSettings({
      home_assistant: HA_BASE,
      storage: STORAGE_BASE,
      plant_identification: { plantnet_api_key_masked: '', source_plantnet_api_key: 'none' },
    });
    const field = await screen.findByTestId('plantnet-key-field');
    const input = field.querySelector('input') as HTMLInputElement;
    expect(input.type).toBe('password');
    await user.click(screen.getByTestId('plantnet-key-visibility-toggle'));
    expect(input.type).toBe('text');
    await user.click(screen.getByTestId('plantnet-key-visibility-toggle'));
    expect(input.type).toBe('password');
  });

  it('runs a successful key test and shows the success alert', async () => {
    const user = userEvent.setup();
    const { getTestBody } = renderSettings(
      {
        home_assistant: HA_BASE,
        storage: STORAGE_BASE,
        plant_identification: { plantnet_api_key_masked: '', source_plantnet_api_key: 'none' },
      },
      { testResult: { success: true, message: 'Key works' } },
    );
    const field = await screen.findByTestId('plantnet-key-field');
    const input = field.querySelector('input') as HTMLInputElement;
    await user.type(input, 'candidate-key');
    await user.click(screen.getByTestId('plantnet-test-btn'));

    const alert = await screen.findByTestId('plantnet-test-result-alert');
    expect(alert).toHaveTextContent('Key works');
    await waitFor(() => expect(getTestBody()).toEqual({ plantnet_api_key: 'candidate-key' }));
  });

  it('shows a failure alert when the key test returns success=false', async () => {
    const user = userEvent.setup();
    renderSettings(
      {
        home_assistant: HA_BASE,
        storage: STORAGE_BASE,
        plant_identification: { plantnet_api_key_masked: '****2345', source_plantnet_api_key: 'db' },
      },
      { testResult: { success: false, message: 'Invalid key' } },
    );
    await screen.findByTestId('plantnet-test-btn');
    // The masked DB key already enables the test button without typing.
    await user.click(screen.getByTestId('plantnet-test-btn'));
    const alert = await screen.findByTestId('plantnet-test-result-alert');
    expect(alert).toHaveTextContent('Invalid key');
  });

  it('shows a network-error alert when the key test request throws', async () => {
    const user = userEvent.setup();
    renderSettings(
      {
        home_assistant: HA_BASE,
        storage: STORAGE_BASE,
        plant_identification: { plantnet_api_key_masked: '****2345', source_plantnet_api_key: 'db' },
      },
      { testFails: true },
    );
    await screen.findByTestId('plantnet-test-btn');
    await user.click(screen.getByTestId('plantnet-test-btn'));
    expect(await screen.findByTestId('plantnet-test-result-alert')).toBeInTheDocument();
  });

  it('disables the test button when no key is entered or stored', async () => {
    renderSettings({
      home_assistant: HA_BASE,
      storage: STORAGE_BASE,
      plant_identification: { plantnet_api_key_masked: '', source_plantnet_api_key: 'none' },
    });
    const testBtn = await screen.findByTestId('plantnet-test-btn');
    expect(testBtn).toBeDisabled();
  });

  it('surfaces a top-level error when saving the key fails', async () => {
    const user = userEvent.setup();
    renderSettings(
      {
        home_assistant: HA_BASE,
        storage: STORAGE_BASE,
        plant_identification: { plantnet_api_key_masked: '', source_plantnet_api_key: 'none' },
      },
      { putFails: true },
    );
    const field = await screen.findByTestId('plantnet-key-field');
    const input = field.querySelector('input') as HTMLInputElement;
    await user.type(input, 'will-fail');
    await user.click(screen.getByTestId('plantnet-save-btn'));
    // The page-level error Alert renders the generic server error message.
    expect(await screen.findByText(/Server error/i)).toBeInTheDocument();
    expect(screen.queryByTestId('plantnet-save-success-alert')).not.toBeInTheDocument();
  });

  it('shows the HA card alongside Pl@ntNet when smart home is enabled', async () => {
    // The page re-fetches preferences on mount, so the server must echo the
    // smart_home flag that gates the HA integration card.
    const prefs = {
      experience_level: 'expert',
      locale: 'de',
      theme: 'light',
      smart_home_enabled: true,
    };
    server.use(
      http.get('/api/v1/t/:tenant/user-preferences', () => HttpResponse.json(prefs)),
      http.get('/api/v1/user-preferences', () => HttpResponse.json(prefs)),
    );
    renderSettings(
      {
        home_assistant: {
          ha_url: 'http://ha.local:8123',
          ha_access_token_masked: '****tok',
          ha_timeout: 10,
          source_ha_url: 'db',
          source_ha_access_token: 'db',
          source_ha_timeout: 'default',
        },
        storage: STORAGE_BASE,
        plant_identification: { plantnet_api_key_masked: '', source_plantnet_api_key: 'none' },
      },
      { smartHomeEnabled: true },
    );
    // Both the HA integration card and the Pl@ntNet card render together.
    expect(await screen.findByTestId('ha-url-field')).toBeInTheDocument();
    expect(screen.getByTestId('plantnet-key-field')).toBeInTheDocument();
  });
});
