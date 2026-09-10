import { Route, Navigate, createBrowserRouter, createRoutesFromElements } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import MainLayout from '@/layouts/MainLayout';
import KioskLayout from '@/layouts/KioskLayout';
import LoadingSkeleton from '@/components/common/LoadingSkeleton';
import ProtectedRoute from '@/auth/ProtectedRoute';
import PublicOnlyRoute from '@/auth/PublicOnlyRoute';
// #1261 — the domain-role guard. Every `<RequireRole>` below must match an entry
// in ROLE_GUARDED_ROUTES, and every route in this file must carry a decision in
// that table; `scripts/check_route_role_guards.py` and
// `src/test/routes/roleRouteGuards.test.tsx` both enforce that pairing, so the
// guard cannot be dropped from a route without a test going red.
import RequireRole from '@/auth/RequireRole';
import RequirePlatformAdmin from '@/auth/RequirePlatformAdmin';
import RouterErrorPage from '@/pages/RouterErrorPage';
import { isLightMode } from '@/config/mode';

// Auth pages
const LoginPage = lazy(() => import('@/pages/auth/LoginPage'));
const RegisterPage = lazy(() => import('@/pages/auth/RegisterPage'));
const EmailVerificationPage = lazy(() => import('@/pages/auth/EmailVerificationPage'));
const PasswordResetRequestPage = lazy(() => import('@/pages/auth/PasswordResetRequestPage'));
const PasswordResetConfirmPage = lazy(() => import('@/pages/auth/PasswordResetConfirmPage'));
const AccountSettingsPage = lazy(() => import('@/pages/auth/AccountSettingsPage'));
const PrivacySettingsPage = lazy(() => import('@/pages/auth/PrivacySettingsPage'));
const OAuthCallbackPage = lazy(() => import('@/pages/auth/OAuthCallbackPage'));
// #1118 P13 — browser landing for the light-mode instance-discovery deep link
// (https://<instance>/connect?v=1). Public and mode-agnostic: a system-camera
// visitor without the app must not hit a 404 or a login bounce.
const ConnectLandingPage = lazy(() => import('@/pages/auth/ConnectLandingPage'));

// Tenant pages
const TenantCreatePage = lazy(() => import('@/pages/tenants/TenantCreatePage'));
const TenantSettingsPage = lazy(() => import('@/pages/tenants/TenantSettingsPage'));
const InvitationAcceptPage = lazy(() => import('@/pages/tenants/InvitationAcceptPage'));

const DashboardPage = lazy(() => import('@/pages/DashboardPage'));
const BotanicalFamilyListPage = lazy(() => import('@/pages/stammdaten/BotanicalFamilyListPage'));
const BotanicalFamilyDetailPage = lazy(
  () => import('@/pages/stammdaten/BotanicalFamilyDetailPage'),
);
const SpeciesListPage = lazy(() => import('@/pages/stammdaten/SpeciesListPage'));
const SpeciesDetailPage = lazy(() => import('@/pages/stammdaten/SpeciesDetailPage'));
const CultivarDetailPage = lazy(() => import('@/pages/stammdaten/CultivarDetailPage'));
const ActivityListPage = lazy(() => import('@/pages/stammdaten/ActivityListPage'));
const ActivityDetailPage = lazy(() => import('@/pages/stammdaten/ActivityDetailPage'));
const CompanionPlantingPage = lazy(() => import('@/pages/stammdaten/CompanionPlantingPage'));
const CropRotationPage = lazy(() => import('@/pages/stammdaten/CropRotationPage'));
// REQ-012 Import
const ImportPage = lazy(() => import('@/pages/stammdaten/ImportPage'));
const SiteListPage = lazy(() => import('@/pages/standorte/SiteListPage'));
const SiteDetailPage = lazy(() => import('@/pages/standorte/SiteDetailPage'));
const LocationDetailPage = lazy(() => import('@/pages/standorte/LocationDetailPage'));
const SubstrateListPage = lazy(() => import('@/pages/standorte/SubstrateListPage'));
const SubstrateDetailPage = lazy(() => import('@/pages/standorte/SubstrateDetailPage'));
const BatchDetailPage = lazy(() => import('@/pages/standorte/BatchDetailPage'));
const SlotDetailPage = lazy(() => import('@/pages/standorte/SlotDetailPage'));
const PlantInstanceListPage = lazy(() => import('@/pages/pflanzen/PlantInstanceListPage'));
const PlantInstanceDetailPage = lazy(() => import('@/pages/pflanzen/PlantInstanceDetailPage'));
const CalculationsPage = lazy(() => import('@/pages/pflanzen/CalculationsPage'));
// REQ-029 / REQ-029-A KI-Pflanzenerkennung
const PlantIdentificationPage = lazy(
  () => import('@/pages/ki-recognition/PlantIdentificationPage'),
);
// REQ-044 Schädlingserkennung (global, plant-agnostic)
const PestIdentificationPage = lazy(() => import('@/pages/ki-recognition/PestIdentificationPage'));
// REQ-031 KI-Assistent & Wissensvermittlung
const KIAssistentPage = lazy(() => import('@/pages/ki-assistent/KIAssistentPage'));
// REQ-035 KI-Glossar
const GlossaryPage = lazy(() => import('@/pages/glossar/GlossaryPage'));
// REQ-036 KI-Diagnose-Assistent
const DiagnosePage = lazy(() => import('@/pages/ki-diagnose/DiagnosePage'));
const PlantingRunListPage = lazy(() => import('@/pages/durchlaeufe/PlantingRunListPage'));
const PlantingRunDetailPage = lazy(() => import('@/pages/durchlaeufe/PlantingRunDetailPage'));
const SuccessionPlanListPage = lazy(() => import('@/pages/durchlaeufe/SuccessionPlanListPage'));
// REQ-022 Überwinterung
const OverwinteringListPage = lazy(() => import('@/pages/ueberwinterung/OverwinteringListPage'));
// REQ-026 Aquaponik
const AquaponikPage = lazy(() => import('@/pages/aquaponik/AquaponikPage'));
// REQ-018 Umgebungssteuerung / Aktorik
const EnvironmentControlPage = lazy(() => import('@/pages/environment/EnvironmentControlPage'));
// REQ-016 InvenTree integration (Equipment + inventory sync)
const InventreePage = lazy(() => import('@/pages/inventree/InventreePage'));
// REQ-017 Vermehrung / Lineage
const PropagationPage = lazy(() => import('@/pages/propagation/PropagationPage'));
const TankListPage = lazy(() => import('@/pages/standorte/TankListPage'));
const TankDetailPage = lazy(() => import('@/pages/standorte/TankDetailPage'));
const FertilizerListPage = lazy(() => import('@/pages/duengung/FertilizerListPage'));
const FertilizerDetailPage = lazy(() => import('@/pages/duengung/FertilizerDetailPage'));
const NutrientPlanListPage = lazy(() => import('@/pages/duengung/NutrientPlanListPage'));
const NutrientPlanDetailPage = lazy(() => import('@/pages/duengung/NutrientPlanDetailPage'));
const NutrientCalculationsPage = lazy(() => import('@/pages/duengung/NutrientCalculationsPage'));
const FeedingEventListPage = lazy(() => import('@/pages/duengung/FeedingEventListPage'));
const FeedingEventDetailPage = lazy(() => import('@/pages/duengung/FeedingEventDetailPage'));
const WateringEventListPage = lazy(() => import('@/pages/standorte/WateringEventListPage'));
// Unified watering log (replaces WateringEvent + FeedingEvent)
const WateringLogListPage = lazy(() => import('@/pages/giessprotokoll/WateringLogListPage'));
const WateringLogDetailPage = lazy(() => import('@/pages/giessprotokoll/WateringLogDetailPage'));
// REQ-051 §6.2 Tagebuch-Übersicht (mandantenweit)
const DiaryOverviewPage = lazy(() => import('@/pages/tagebuch/DiaryOverviewPage'));
// REQ-010 IPM
const PestListPage = lazy(() => import('@/pages/pflanzenschutz/PestListPage'));
const PestDetailPage = lazy(() => import('@/pages/pflanzenschutz/PestDetailPage'));
const DiseaseListPage = lazy(() => import('@/pages/pflanzenschutz/DiseaseListPage'));
const TreatmentListPage = lazy(() => import('@/pages/pflanzenschutz/TreatmentListPage'));
const TreatmentDetailPage = lazy(() => import('@/pages/pflanzenschutz/TreatmentDetailPage'));
// REQ-007 Harvest
const HarvestBatchListPage = lazy(() => import('@/pages/ernte/HarvestBatchListPage'));
const HarvestBatchDetailPage = lazy(() => import('@/pages/ernte/HarvestBatchDetailPage'));
// REQ-008 Post-Harvest
const PostHarvestPage = lazy(() => import('@/pages/post-harvest/PostHarvestPage'));
// REQ-006 Tasks
const TaskQueuePage = lazy(() => import('@/pages/aufgaben/TaskQueuePage'));
const TaskDetailPage = lazy(() => import('@/pages/aufgaben/TaskDetailPage'));
const WorkflowDetailPage = lazy(() => import('@/pages/aufgaben/WorkflowDetailPage'));
const WorkflowTemplateListPage = lazy(() => import('@/pages/aufgaben/WorkflowTemplateListPage'));

// REQ-003 Phase Definitions & Sequences
const PhaseDefinitionListPage = lazy(() => import('@/pages/phasen/PhaseDefinitionListPage'));
const PhaseDefinitionDetailPage = lazy(() => import('@/pages/phasen/PhaseDefinitionDetailPage'));
const PhaseSequenceListPage = lazy(() => import('@/pages/phasen/PhaseSequenceListPage'));
const PhaseSequenceDetailPage = lazy(() => import('@/pages/phasen/PhaseSequenceDetailPage'));

// REQ-015 Kalender
const CalendarPage = lazy(() => import('@/pages/kalender/CalendarPage'));
// REQ-020 Onboarding
const OnboardingWizard = lazy(() => import('@/pages/onboarding/OnboardingWizard'));

// Admin
const AdminEditTenantPage = lazy(() => import('@/pages/admin/AdminEditTenantPage'));
const AdminEditUserPage = lazy(() => import('@/pages/admin/AdminEditUserPage'));

// UI-NFR-019 Kiosk mode
const KioskStartPage = lazy(() => import('@/pages/kiosk/KioskStartPage'));

const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'));

export const router = createBrowserRouter(
  createRoutesFromElements(
    <Route errorElement={<RouterErrorPage />}>
      {/* #1118 P13 — instance-discovery deep-link landing. Public and
          mode-agnostic (outside ProtectedRoute and the light/full gating): the
          light-mode "Connect app" QR encodes https://<instance>/connect?v=1, and
          a phone camera opening it without the installed app must land here, not
          on a 404 or a login redirect. The future Android app catches the same
          URL via a wildcard-host intent-filter before the browser is involved. */}
      <Route
        path="connect"
        element={
          <Suspense fallback={<LoadingSkeleton variant="card" />}>
            <ConnectLandingPage />
          </Suspense>
        }
      />

      {/* OAuth callback — full mode only */}
      {!isLightMode && (
        <Route
          path="auth/callback"
          element={
            <Suspense fallback={<LoadingSkeleton variant="card" />}>
              <OAuthCallbackPage />
            </Suspense>
          }
        />
      )}

      {/* Public-only routes (redirect to dashboard when authenticated) — full mode only */}
      {!isLightMode && (
        <Route element={<PublicOnlyRoute />}>
          <Route
            path="login"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <LoginPage />
              </Suspense>
            }
          />
          <Route
            path="register"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <RegisterPage />
              </Suspense>
            }
          />
          <Route
            path="verify-email/:token"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <EmailVerificationPage />
              </Suspense>
            }
          />
          <Route
            path="password-reset"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <PasswordResetRequestPage />
              </Suspense>
            }
          />
          <Route
            path="password-reset/:token"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <PasswordResetConfirmPage />
              </Suspense>
            }
          />
        </Route>
      )}

      {/* Protected routes (require authentication) */}
      <Route element={<ProtectedRoute />}>
        {/* UI-NFR-019 Kiosk mode — dedicated shell (no sidebar/breadcrumb) */}
        <Route path="kiosk" element={<KioskLayout />}>
          <Route
            index
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <KioskStartPage />
              </Suspense>
            }
          />
        </Route>

        <Route element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route
            path="dashboard"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <DashboardPage />
              </Suspense>
            }
          />

          {/* Account Settings */}
          <Route
            path="settings"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <AccountSettingsPage />
              </Suspense>
            }
          />

          {/* REQ-025 Datenschutz & Betroffenenrechte (DSGVO) — full mode only
              (per-registered-user self-service; light mode is anonymous) */}
          {!isLightMode && (
            <Route
              path="privacy"
              element={
                <Suspense fallback={<LoadingSkeleton variant="form" />}>
                  <PrivacySettingsPage />
                </Suspense>
              }
            />
          )}

          {/* Admin: Edit tenant/user — full mode only.
              REQ-049 §2.4 / #1336: the platform-admin axis, guarded by its own
              wrapper. Every request these pages make is `require_platform_admin`,
              the reads included, so refusal replaces the page instead of
              restricting it — the decision and its measurement are in
              PLATFORM_ADMIN_ROUTES. */}
          {!isLightMode && (
            <>
              <Route
                path="admin/tenants/:key"
                element={
                  <RequirePlatformAdmin>
                    <Suspense fallback={<LoadingSkeleton variant="form" />}>
                      <AdminEditTenantPage />
                    </Suspense>
                  </RequirePlatformAdmin>
                }
              />
              <Route
                path="admin/users/:key"
                element={
                  <RequirePlatformAdmin>
                    <Suspense fallback={<LoadingSkeleton variant="form" />}>
                      <AdminEditUserPage />
                    </Suspense>
                  </RequirePlatformAdmin>
                }
              />
            </>
          )}

          {/* REQ-024 Tenants — full mode only */}
          {!isLightMode && (
            <>
              <Route
                path="tenants/create"
                element={
                  <Suspense fallback={<LoadingSkeleton variant="form" />}>
                    <TenantCreatePage />
                  </Suspense>
                }
              />
              <Route
                path="tenants/settings"
                element={
                  <Suspense fallback={<LoadingSkeleton variant="form" />}>
                    <TenantSettingsPage />
                  </Suspense>
                }
              />
              <Route
                path="invitations/accept"
                element={
                  <Suspense fallback={<LoadingSkeleton variant="card" />}>
                    <InvitationAcceptPage />
                  </Suspense>
                }
              />
            </>
          )}

          {/* REQ-022 Pflege — merged into aufgaben/queue */}
          <Route path="pflege" element={<Navigate to="/aufgaben/queue" replace />} />

          {/* REQ-022 Überwinterung */}
          <Route
            path="ueberwinterung/profile"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <OverwinteringListPage />
              </Suspense>
            }
          />

          {/* REQ-015 Kalender */}
          <Route
            path="kalender"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <CalendarPage />
              </Suspense>
            }
          />

          {/* REQ-020 Onboarding */}
          <Route
            path="onboarding"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <OnboardingWizard />
              </Suspense>
            }
          />

          {/* REQ-001 Stammdaten */}
          <Route
            path="stammdaten/botanical-families"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <BotanicalFamilyListPage />
              </Suspense>
            }
          />
          <Route
            path="stammdaten/botanical-families/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <BotanicalFamilyDetailPage />
              </Suspense>
            }
          />
          <Route
            path="stammdaten/species"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <SpeciesListPage />
              </Suspense>
            }
          />
          <Route
            path="stammdaten/species/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <SpeciesDetailPage />
              </Suspense>
            }
          />
          <Route
            path="stammdaten/species/:speciesKey/cultivars/:cultivarKey"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <CultivarDetailPage />
              </Suspense>
            }
          />
          <Route
            path="stammdaten/companion-planting"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <CompanionPlantingPage />
              </Suspense>
            }
          />
          <Route
            path="stammdaten/crop-rotation"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <CropRotationPage />
              </Suspense>
            }
          />
          {/* Activities */}
          <Route
            path="stammdaten/activities"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <ActivityListPage />
              </Suspense>
            }
          />
          <Route
            path="stammdaten/activities/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <ActivityDetailPage />
              </Suspense>
            }
          />
          {/* REQ-012 Import */}
          <Route
            path="stammdaten/import"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <ImportPage />
              </Suspense>
            }
          />

          {/* REQ-002 Standorte */}
          <Route
            path="standorte/sites"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <SiteListPage />
              </Suspense>
            }
          />
          <Route
            path="standorte/sites/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <SiteDetailPage />
              </Suspense>
            }
          />
          <Route
            path="standorte/locations/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <LocationDetailPage />
              </Suspense>
            }
          />
          <Route
            path="standorte/substrates"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <SubstrateListPage />
              </Suspense>
            }
          />
          <Route
            path="standorte/substrates/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <SubstrateDetailPage />
              </Suspense>
            }
          />
          <Route
            path="standorte/substrates/batches/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <BatchDetailPage />
              </Suspense>
            }
          />
          <Route
            path="standorte/slots/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <SlotDetailPage />
              </Suspense>
            }
          />

          {/* REQ-014 Watering Events */}
          <Route
            path="standorte/watering-events"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <WateringEventListPage />
              </Suspense>
            }
          />

          {/* REQ-026 Aquaponik — creating a system needs grower (#1261) */}
          <Route
            path="aquaponik"
            element={
              <RequireRole min="grower">
                <Suspense fallback={<LoadingSkeleton variant="card" />}>
                  <AquaponikPage />
                </Suspense>
              </RequireRole>
            }
          />

          {/* REQ-018 Umgebungssteuerung / Aktorik */}
          <Route
            path="umgebungssteuerung"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <EnvironmentControlPage />
              </Suspense>
            }
          />

          {/* REQ-016 InvenTree integration — creating equipment needs grower (#1261) */}
          <Route
            path="inventree"
            element={
              <RequireRole min="grower">
                <Suspense fallback={<LoadingSkeleton variant="table" />}>
                  <InventreePage />
                </Suspense>
              </RequireRole>
            }
          />

          {/* REQ-017 Vermehrung / Lineage — recording an event needs grower (#1261) */}
          <Route
            path="vermehrung"
            element={
              <RequireRole min="grower">
                <Suspense fallback={<LoadingSkeleton variant="table" />}>
                  <PropagationPage />
                </Suspense>
              </RequireRole>
            }
          />

          {/* REQ-014 Tanks */}
          <Route
            path="standorte/tanks"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <TankListPage />
              </Suspense>
            }
          />
          <Route
            path="standorte/tanks/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <TankDetailPage />
              </Suspense>
            }
          />

          {/* REQ-003 Pflanzen */}
          <Route
            path="pflanzen/plant-instances"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <PlantInstanceListPage />
              </Suspense>
            }
          />
          <Route
            path="pflanzen/plant-instances/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <PlantInstanceDetailPage />
              </Suspense>
            }
          />
          <Route
            path="pflanzen/calculations"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <CalculationsPage />
              </Suspense>
            }
          />
          {/* REQ-029 / REQ-029-A KI-Pflanzenerkennung — identifying needs grower
              (#1256/#1260 gated the write, #1261 stops offering it to a viewer);
              the history below it stays readable for every member */}
          <Route
            path="pflanzen/identifikation"
            element={
              <RequireRole min="grower">
                <Suspense fallback={<LoadingSkeleton variant="card" />}>
                  <PlantIdentificationPage />
                </Suspense>
              </RequireRole>
            }
          />
          {/* REQ-031 KI-Assistent & Wissensvermittlung */}
          <Route
            path="ki-assistent"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <KIAssistentPage />
              </Suspense>
            }
          />
          {/* REQ-035 KI-Fachbegriff-Glossar — light-mode-fähig (kein Consent, §6) */}
          <Route
            path="glossar"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <GlossaryPage />
              </Suspense>
            }
          />
          {/* REQ-036 KI-Diagnose-Assistent (strukturiert, symptombasiert) */}
          <Route
            path="diagnose"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <DiagnosePage />
              </Suspense>
            }
          />

          {/* REQ-004 Düngung */}
          <Route
            path="duengung/fertilizers"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <FertilizerListPage />
              </Suspense>
            }
          />
          <Route
            path="duengung/fertilizers/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <FertilizerDetailPage />
              </Suspense>
            }
          />
          <Route
            path="duengung/plans"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <NutrientPlanListPage />
              </Suspense>
            }
          />
          <Route
            path="duengung/plans/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <NutrientPlanDetailPage />
              </Suspense>
            }
          />
          <Route
            path="duengung/calculations"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <NutrientCalculationsPage />
              </Suspense>
            }
          />

          {/* REQ-004 Feeding Events */}
          <Route
            path="duengung/feeding-events"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <FeedingEventListPage />
              </Suspense>
            }
          />
          <Route
            path="duengung/feeding-events/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <FeedingEventDetailPage />
              </Suspense>
            }
          />

          {/* Watering Log (unified) */}
          <Route
            path="giessprotokoll"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <WateringLogListPage />
              </Suspense>
            }
          />
          <Route
            path="giessprotokoll/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <WateringLogDetailPage />
              </Suspense>
            }
          />

          {/* REQ-051 §6.2 — mandantenweite Tagebuch-Übersicht. Kein eigener
              Guard: alle Routen unter MainLayout laufen durch ModuleGuard, der
              den Pfad über das Modul `diary` auflöst (AK-31). */}
          <Route
            path="tagebuch"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <DiaryOverviewPage />
              </Suspense>
            }
          />

          {/* REQ-044 Schädlingserkennung (global, plant-agnostic) */}
          <Route
            path="pflanzenschutz/erkennung"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <PestIdentificationPage />
              </Suspense>
            }
          />

          {/* REQ-010 Pflanzenschutz */}
          <Route
            path="pflanzenschutz/pests"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <PestListPage />
              </Suspense>
            }
          />
          <Route
            path="pflanzenschutz/pests/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <PestDetailPage />
              </Suspense>
            }
          />
          <Route
            path="pflanzenschutz/diseases"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <DiseaseListPage />
              </Suspense>
            }
          />
          <Route
            path="pflanzenschutz/treatments"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <TreatmentListPage />
              </Suspense>
            }
          />
          <Route
            path="pflanzenschutz/treatments/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <TreatmentDetailPage />
              </Suspense>
            }
          />

          {/* REQ-007 Ernte */}
          <Route
            path="ernte/batches"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <HarvestBatchListPage />
              </Suspense>
            }
          />
          <Route
            path="ernte/batches/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <HarvestBatchDetailPage />
              </Suspense>
            }
          />

          {/* REQ-008 Nacherntebehandlung — starting a drying run needs grower (#1261) */}
          <Route
            path="ernte/nachernte"
            element={
              <RequireRole min="grower">
                <Suspense fallback={<LoadingSkeleton variant="table" />}>
                  <PostHarvestPage />
                </Suspense>
              </RequireRole>
            }
          />

          {/* REQ-006 Aufgaben */}
          <Route
            path="aufgaben/queue"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <TaskQueuePage />
              </Suspense>
            }
          />
          <Route
            path="aufgaben/tasks/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <TaskDetailPage />
              </Suspense>
            }
          />
          <Route
            path="aufgaben/workflows/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <WorkflowDetailPage />
              </Suspense>
            }
          />
          <Route
            path="aufgaben/workflows"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <WorkflowTemplateListPage />
              </Suspense>
            }
          />
          <Route
            path="aufgaben/activity-plans"
            element={<Navigate to="/stammdaten/species" replace />}
          />
          <Route
            path="aufgaben/activity-plans/:speciesKey"
            element={<Navigate to="/aufgaben/workflows" replace />}
          />

          {/* REQ-003 Phase Definitions & Sequences */}
          <Route
            path="phasen/definitionen"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <PhaseDefinitionListPage />
              </Suspense>
            }
          />
          <Route
            path="phasen/definitionen/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <PhaseDefinitionDetailPage />
              </Suspense>
            }
          />
          <Route
            path="phasen/ablaeufe"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <PhaseSequenceListPage />
              </Suspense>
            }
          />
          <Route
            path="phasen/ablaeufe/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <PhaseSequenceDetailPage />
              </Suspense>
            }
          />

          {/* REQ-013 Durchläufe */}
          <Route
            path="durchlaeufe/planting-runs"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <PlantingRunListPage />
              </Suspense>
            }
          />
          <Route
            path="durchlaeufe/planting-runs/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="form" />}>
                <PlantingRunDetailPage />
              </Suspense>
            }
          />

          {/* REQ-013 §2 Staffelanbau / Succession plans */}
          <Route
            path="durchlaeufe/succession-plans"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <SuccessionPlanListPage />
              </Suspense>
            }
          />
          <Route
            path="durchlaeufe/succession-plans/:key"
            element={
              <Suspense fallback={<LoadingSkeleton variant="table" />}>
                <SuccessionPlanListPage />
              </Suspense>
            }
          />

          <Route
            path="*"
            element={
              <Suspense fallback={<LoadingSkeleton variant="card" />}>
                <NotFoundPage />
              </Suspense>
            }
          />
        </Route>
      </Route>
    </Route>,
  ),
);
