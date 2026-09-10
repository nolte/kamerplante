import { useState, useEffect, useRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import Dialog from '@mui/material/Dialog';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import Divider from '@mui/material/Divider';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import Tooltip from '@mui/material/Tooltip';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import Form from '@/components/form/Form';
import FormTextField from '@/components/form/FormTextField';
import FormSelectField from '@/components/form/FormSelectField';
import FormDateField from '@/components/form/FormDateField';
import FormActions from '@/components/form/FormActions';
import FormRow from '@/components/form/FormRow';
import SubstrateSelectField from '@/components/form/SubstrateSelectField';
import SpeciesAutocompleteField from '@/components/form/SpeciesAutocompleteField';
import LocationAssignmentSection from '@/components/form/LocationAssignmentSection';
import FavoriteToggle from '@/components/common/FavoriteToggle';
import { useNotification } from '@/hooks/useNotification';
import { useApiError } from '@/hooks/useApiError';
import { useSowingFavorites } from '@/hooks/useSowingFavorites';
import * as plantApi from '@/api/endpoints/plantInstances';
import * as speciesApi from '@/api/endpoints/species';
import { uploadPlantPhoto } from '@/api/endpoints/plantPhotos';
import { contributeReferenceImage } from '@/api/endpoints/identification';
import * as phaseApi from '@/api/endpoints/phases';
import * as phaseSequenceApi from '@/api/endpoints/phaseSequences';
import * as substrateApi from '@/api/endpoints/substrates';
import * as sitesApi from '@/api/endpoints/sites';
import type { Species, Cultivar, Substrate, SubstrateType, Site, Slot } from '@/api/types';
import { generateInstanceId } from '@/utils/idGenerator';

const schema = z.object({
  instance_id: z.string().min(1),
  species_key: z.string().min(1),
  cultivar_key: z.string().nullable(),
  plant_name: z.string().nullable(),
  planted_on: z.string().min(1),
  current_phase_key: z.string().nullable(),
  // ADR-006 E1 (#565) — per-instance cultivation cycle override; '' = same as the species.
  cultivation_cycle_type: z.enum(['', 'annual', 'biennial', 'perennial']),
  substrate_key: z.string().nullable(),
  site_key: z.string().nullable(),
  location_key: z.string().nullable(),
  slot_key: z.string().nullable(),
});

type FormData = z.infer<typeof schema>;

/**
 * A start-phase option normalized from either source (issue #626): a
 * PhaseSequence entry or a LifecycleConfig growth phase. `key` is the value the
 * backend validates against (`_valid_phase_keys`); `name`/`displayName` drive
 * the human-readable label (display name first, i18n phase-name fallback).
 */
interface PhaseOptionSource {
  key: string;
  displayName: string | null;
  name: string;
}

export interface PlantInstanceDuplicateData {
  species_key: string;
  cultivar_key: string | null;
  plant_name: string | null;
  substrate_key: string | null;
  substrate_type_override: SubstrateType | null;
  current_phase_key: string | null;
  slot_key: string | null;
}

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: (key: string) => void;
  initialSpeciesKey?: string;
  duplicateFrom?: PlantInstanceDuplicateData;
  /**
   * Photo captured during plant identification (issue #447). When present, the
   * dialog offers to reuse it: as the new instance's gallery cover (default on)
   * and — in DINOv2 mode — as a few-shot recognition reference (default off).
   */
  identificationPhoto?: File;
  /**
   * Whether the self-hosted DINOv2 recognition path is active. Gates the
   * "use as recognition reference" toggle; the external Pl@ntNet path has no
   * local reference index, so the toggle is hidden when this is false.
   */
  allowReferenceContribution?: boolean;
}

export default function PlantInstanceCreateDialog({
  open,
  onClose,
  onCreated,
  initialSpeciesKey,
  duplicateFrom,
  identificationPhoto,
  allowReferenceContribution = false,
}: Props) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const { t } = useTranslation();
  const notification = useNotification();
  const { handleError } = useApiError();
  const { isFavorite, toggleFavorite } = useSowingFavorites();
  const [saving, setSaving] = useState(false);
  const [speciesList, setSpeciesList] = useState<Species[]>([]);
  const [cultivarList, setCultivarList] = useState<Cultivar[]>([]);
  const [cultivarsLoading, setCultivarsLoading] = useState(false);
  const [substratesList, setSubstratesList] = useState<Substrate[]>([]);
  // Normalized start-phase options for the "Current Phase" select. The source
  // (PhaseSequence entries vs LifecycleConfig growth phases) is resolved the
  // same way the backend validates (issue #626), so the stored keys are always
  // members of the backend's `_valid_phase_keys` set.
  const [phaseOptionSources, setPhaseOptionSources] = useState<PhaseOptionSource[]>([]);
  const [sitesList, setSitesList] = useState<Site[]>([]);
  const [slotsList, setSlotsList] = useState<Slot[]>([]);

  // ── Identification photo carry-over (issue #447) ─────────────────────
  const [saveAsGalleryPhoto, setSaveAsGalleryPhoto] = useState(true);
  const [useAsReference, setUseAsReference] = useState(false);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | null>(null);

  // Build (and revoke) a preview URL for the carried-over photo. The File is
  // owned by the caller; we only manage the object URL created here. This is a
  // genuine external-system sync (Object-URL lifecycle), so the setState is
  // intentional.
  useEffect(() => {
    if (!identificationPhoto) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPhotoPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(identificationPhoto);
    setPhotoPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [identificationPhoto]);

  // Reset the toggles to their defaults each time the dialog (re)opens, mirroring
  // the form reset above.
  useEffect(() => {
    if (open) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSaveAsGalleryPhoto(true);
      setUseAsReference(false);
    }
  }, [open]);

  const { control, handleSubmit, reset, setValue, getValues } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      instance_id: '',
      species_key: '',
      cultivar_key: null,
      plant_name: null,
      planted_on: new Date().toISOString().split('T')[0],
      current_phase_key: null,
      cultivation_cycle_type: '',
      substrate_key: null,
      site_key: null,
      location_key: null,
      slot_key: null,
    },
  });

  const speciesKey = useWatch({ control, name: 'species_key' });
  const siteKey = useWatch({ control, name: 'site_key' });
  const locationKey = useWatch({ control, name: 'location_key' });

  // ADR-006 E6 (#615): only species that are genuinely facultative (can be grown
  // annual OR perennial) may offer the per-instance cultivation-cycle choice. For
  // any other species the cycle follows the species default, so the select is
  // hidden and an informative caption explains that.
  const selectedSpecies = useMemo(
    () => speciesList.find((s) => s.key === speciesKey) ?? null,
    [speciesList, speciesKey],
  );
  const cultivationFlexible = selectedSpecies?.cultivation_flexible ?? false;

  const effectiveSpeciesKey = duplicateFrom?.species_key ?? initialSpeciesKey ?? '';

  useEffect(() => {
    if (open) {
      const substrateVal = duplicateFrom?.substrate_key
        ? duplicateFrom.substrate_key
        : duplicateFrom?.substrate_type_override
          ? `_type_${duplicateFrom.substrate_type_override}`
          : null;
      reset({
        instance_id: generateInstanceId(''),
        species_key: effectiveSpeciesKey,
        cultivar_key: duplicateFrom?.cultivar_key ?? null,
        plant_name: duplicateFrom?.plant_name ? `${duplicateFrom.plant_name} (Kopie)` : null,
        planted_on: new Date().toISOString().split('T')[0],
        current_phase_key: duplicateFrom?.current_phase_key ?? null,
        cultivation_cycle_type: '',
        substrate_key: substrateVal,
        site_key: null,
        location_key: null,
        slot_key: null,
      });
      substrateApi.listSubstrates(0, 200).then(setSubstratesList).catch(() => setSubstratesList([]));
      sitesApi.listSites(0, 200).then(setSitesList).catch(() => setSitesList([]));
      speciesApi.listSpecies(0, 200).then((r) => {
        setSpeciesList(r.items);
        if (effectiveSpeciesKey) {
          const species = r.items.find((s) => s.key === effectiveSpeciesKey);
          if (species) {
            setValue('instance_id', generateInstanceId(species.scientific_name));
          }
        }
      }).catch(() => {});
      // Resolve slot → location → site for duplicate
      if (duplicateFrom?.slot_key) {
        sitesApi.getSlot(duplicateFrom.slot_key).then(async (slot) => {
          const loc = await sitesApi.getLocation(slot.location_key);
          // Load slots for the location so the dropdown is populated
          const slots = await sitesApi.listSlots(loc.key).catch(() => [] as Slot[]);
          setSlotsList(slots);
          // Set values without triggering cascade resets
          skipLocationReset.current = true;
          skipSlotReset.current = true;
          setValue('site_key', loc.site_key);
          setValue('location_key', loc.key);
          setValue('slot_key', slot.key);
        }).catch(() => {});
      }
    }
  }, [open, reset, effectiveSpeciesKey, setValue, duplicateFrom]);

  useEffect(() => {
    if (speciesKey) {
      const currentId = getValues('instance_id');
      if (currentId.startsWith('PLANT-')) {
        const species = speciesList.find((s) => s.key === speciesKey);
        if (species) {
          setValue('instance_id', generateInstanceId(species.scientific_name));
        }
      }
    }
  }, [speciesKey, speciesList, getValues, setValue]);

  const [initialLoadDone, setInitialLoadDone] = useState(false);

  useEffect(() => {
    if (!open) {
      setInitialLoadDone(false);
    }
  }, [open]);

  useEffect(() => {
    if (!speciesKey) {
      setCultivarList([]);
      setPhaseOptionSources([]);
      return;
    }
    const isInitialDuplicate = duplicateFrom && !initialLoadDone;
    setCultivarsLoading(true);
    if (!isInitialDuplicate) {
      setValue('cultivar_key', null);
      setValue('current_phase_key', null);
    }
    speciesApi
      .listCultivars(speciesKey)
      .then((cultivars) => setCultivarList(cultivars))
      .catch(() => setCultivarList([]))
      .finally(() => setCultivarsLoading(false));

    // Resolve the start-phase options the SAME way the backend validates them
    // (issue #626): a species' PhaseSequence entry keys are authoritative; only a
    // species without a sequence falls back to the LifecycleConfig growth phases.
    // This guarantees the auto-selected default `current_phase_key` is always a
    // member of the backend's `_valid_phase_keys` set, so an unchanged form no
    // longer 422s with PHASE_NOT_IN_SEQUENCE.
    phaseSequenceApi
      .getSpeciesPhaseSequence(speciesKey)
      .then(async (seq): Promise<PhaseOptionSource[]> => {
        if (seq && seq.entries.length > 0) {
          return [...seq.entries]
            .sort((a, b) => a.sequence_order - b.sequence_order)
            .map((entry) => ({
              key: entry.key,
              displayName: entry.phase_definition?.display_name || null,
              name: entry.phase_definition?.name ?? entry.key,
            }));
        }
        // No PhaseSequence → fall back to the LifecycleConfig growth phases
        // (unchanged behaviour for LifecycleConfig-only species).
        const lifecycle = await phaseApi.getLifecycleConfig(speciesKey);
        const phases = await phaseApi.listGrowthPhases(lifecycle.key);
        return [...phases]
          .sort((a, b) => a.sequence_order - b.sequence_order)
          .map((gp) => ({
            key: gp.key,
            displayName: gp.display_name || null,
            name: gp.name,
          }));
      })
      .then((sources) => {
        setPhaseOptionSources(sources);
        // Auto-select the first phase only when the caller did not carry one over
        // (the duplicate path preserves its explicit `current_phase_key`).
        if (!isInitialDuplicate && sources.length > 0) {
          setValue('current_phase_key', sources[0].key);
        }
        setInitialLoadDone(true);
      })
      .catch(() => {
        setPhaseOptionSources([]);
        setInitialLoadDone(true);
      });
  }, [speciesKey, setValue, duplicateFrom, initialLoadDone, open]);

  // Human-readable, i18n-aware option list for the "Current Phase" select. Both
  // sources are normalized to `{ value, label }` so the dropdown renders
  // identically regardless of the resolved phase source (issue #626).
  const phaseOptions = useMemo(
    () =>
      phaseOptionSources.map((src) => ({
        value: src.key,
        label: src.displayName || t(`enums.phaseName.${src.name}`, { defaultValue: src.name }),
      })),
    [phaseOptionSources, t],
  );

  // Keep the per-instance cultivation-cycle override consistent with the gate: a
  // non-facultative species has no cycle choice, so any value carried over from a
  // previously-selected facultative species is reset to "same as the species".
  useEffect(() => {
    if (speciesKey && !cultivationFlexible) {
      setValue('cultivation_cycle_type', '');
    }
  }, [speciesKey, cultivationFlexible, setValue]);

  // Cascade: site → load locations (via LocationTreeSelect), location → load slots
  const skipLocationReset = useRef(false);
  const skipSlotReset = useRef(false);

  useEffect(() => {
    if (skipLocationReset.current) {
      skipLocationReset.current = false;
      return;
    }
    setValue('location_key', null);
    setSlotsList([]);
    setValue('slot_key', null);
  }, [siteKey, setValue]);

  useEffect(() => {
    if (skipSlotReset.current) {
      skipSlotReset.current = false;
      return;
    }
    setSlotsList([]);
    setValue('slot_key', null);
    if (locationKey) {
      sitesApi.listSlots(locationKey).then(setSlotsList).catch(() => setSlotsList([]));
    }
  }, [locationKey, setValue]);

  const onSubmit = async (data: FormData) => {
    try {
      setSaving(true);
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { substrate_key: rawSubstrateKey, site_key: _siteKey, cultivation_cycle_type: cycle, ...rest } = data;
      // Type-only fallback keys start with '_type_' — don't send as substrate_key
      const isTypeOnly = rawSubstrateKey?.startsWith('_type_');
      const substrateKey = isTypeOnly ? null : (rawSubstrateKey || null);
      const selectedSubstrate = substrateKey ? substratesList.find((s) => s.key === substrateKey) : null;
      const typeOverride = isTypeOnly
        ? rawSubstrateKey!.replace('_type_', '') as SubstrateType
        : (selectedSubstrate?.type ?? null);
      const result = await plantApi.createPlantInstance({
        ...rest,
        // See PlantInstanceDetailPage: the "—" option is value '', and '' is not
        // a key — the API refuses it with 422. null is how this API says "none".
        cultivar_key: rest.cultivar_key || null,
        location_key: rest.location_key || null,
        slot_key: rest.slot_key || null,
        substrate_key: substrateKey,
        substrate_type_override: typeOverride,
        // ADR-006 E1 (#565): '' = "same as the species" → send null (inherit default).
        cultivation_cycle_type: cycle || null,
      });
      notification.success(t('common.create'));

      // Carry the identification photo over (issue #447). Both actions are
      // best-effort: the plant is already created, so a failed photo upload or
      // reference indexing must not surface as a create failure — we warn
      // instead and still complete the flow.
      if (identificationPhoto && saveAsGalleryPhoto) {
        try {
          await uploadPlantPhoto(result.key, identificationPhoto);
        } catch {
          notification.warning(t('pages.plantInstances.identificationPhoto.uploadFailed'));
        }
      }
      if (identificationPhoto && allowReferenceContribution && useAsReference) {
        try {
          const species = speciesList.find((s) => s.key === data.species_key);
          await contributeReferenceImage(
            data.species_key,
            species?.scientific_name ?? '',
            identificationPhoto,
          );
        } catch {
          notification.warning(t('pages.plantInstances.identificationPhoto.referenceFailed'));
        }
      }

      reset();
      onCreated(result.key);
    } catch (err) {
      handleError(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog fullScreen={fullScreen} open={open} onClose={onClose} maxWidth="sm" fullWidth aria-labelledby="plant-instance-create-dialog-title" data-testid="plant-instance-create-dialog">
      <DialogTitle id="plant-instance-create-dialog-title">{duplicateFrom ? t('pages.plantInstances.duplicateTitle') : t('pages.plantInstances.create')}</DialogTitle>
      <DialogContent>
        <Form onSubmit={handleSubmit(onSubmit)}>
          {/* Identification */}
          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
              <SpeciesAutocompleteField
                name="species_key"
                control={control}
                label={t('entities.species')}
                required
                autoFocus
                disabled={!!initialSpeciesKey || !!duplicateFrom}
                species={speciesList}
              />
            </Box>
            {/* Mark the selected species as a favorite right here — reuses the
                backend-persisted favorites feature (issue #546). Only actionable
                once a species is picked, so it is disabled while empty. Aligned
                to the input row (mt) rather than the field box, which includes
                helper text. */}
            <Box sx={{ mt: 1, flexShrink: 0 }}>
              <FavoriteToggle
                favorited={!!speciesKey && isFavorite(speciesKey)}
                onToggle={() => {
                  if (speciesKey) {
                    toggleFavorite(speciesKey);
                  }
                }}
                disabled={!speciesKey}
                testId="species"
              />
            </Box>
          </Box>
          <FormRow>
            <FormSelectField
              name="cultivar_key"
              control={control}
              label={t('pages.plantInstances.cultivarKey')}
              helperText={t('pages.plantInstances.cultivarKeyHelper')}
              disabled={!speciesKey || cultivarsLoading}
              options={[
                { value: '', label: '—' },
                ...cultivarList.map((c) => ({ value: c.key, label: c.name })),
              ]}
            />
            <FormTextField
              name="plant_name"
              control={control}
              label={t('pages.plantInstances.plantName')}
              helperText={t('pages.plantInstances.plantNameHelper')}
            />
          </FormRow>

          {/* Identification photo carry-over (issue #447). Only shown when the
              plant was reached via the "identify by photo" flow. */}
          {identificationPhoto && (
            <>
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                {t('pages.plantInstances.identificationPhoto.sectionTitle')}
              </Typography>
              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                spacing={2}
                sx={{ alignItems: { xs: 'stretch', sm: 'flex-start' } }}
                data-testid="identification-photo-section"
              >
                {photoPreviewUrl && (
                  <Box
                    component="img"
                    src={photoPreviewUrl}
                    alt={t('pages.plantInstances.identificationPhoto.previewAlt')}
                    sx={{
                      width: { xs: '100%', sm: 96 },
                      height: { xs: 160, sm: 96 },
                      objectFit: 'cover',
                      borderRadius: 1,
                      bgcolor: 'action.hover',
                      flexShrink: 0,
                    }}
                    data-testid="identification-photo-preview"
                  />
                )}
                <Box sx={{ flexGrow: 1 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={saveAsGalleryPhoto}
                        onChange={(e) => setSaveAsGalleryPhoto(e.target.checked)}
                        slotProps={{
                          input: {
                            'aria-label': t('pages.plantInstances.identificationPhoto.saveToGallery'),
                          },
                        }}
                        data-testid="toggle-save-gallery-photo"
                      />
                    }
                    label={t('pages.plantInstances.identificationPhoto.saveToGallery')}
                    sx={{ minHeight: 48, ml: 0 }}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                    {t('pages.plantInstances.identificationPhoto.saveToGalleryHelper')}
                  </Typography>

                  {/* DINOv2-only: reuse as a few-shot recognition reference. */}
                  {allowReferenceContribution && (
                    <>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={useAsReference}
                              onChange={(e) => setUseAsReference(e.target.checked)}
                              slotProps={{
                                input: {
                                  'aria-label': t(
                                    'pages.plantInstances.identificationPhoto.useAsReference',
                                  ),
                                },
                              }}
                              data-testid="toggle-use-as-reference"
                            />
                          }
                          label={t('pages.plantInstances.identificationPhoto.useAsReference')}
                          sx={{ minHeight: 48, ml: 0 }}
                        />
                        <Tooltip
                          title={t('pages.plantInstances.identificationPhoto.useAsReferenceHint')}
                          placement="top"
                          arrow
                        >
                          {/* Boxed trigger (not the bare 16px icon) so the tap target reaches
                              the WCAG 2.5.8 / UI-NFR-001 R-011 minimum — mirrors the shared
                              HelpTooltip's iconOnly trigger for consistency. */}
                          <Box
                            component="span"
                            tabIndex={0}
                            aria-label={t('pages.plantInstances.identificationPhoto.useAsReferenceHint')}
                            sx={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              minWidth: 24,
                              minHeight: 24,
                              p: '4px',
                              cursor: 'help',
                            }}
                          >
                            <InfoOutlinedIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
                          </Box>
                        </Tooltip>
                      </Box>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        {t('pages.plantInstances.identificationPhoto.useAsReferenceHelper')}
                      </Typography>
                    </>
                  )}
                </Box>
              </Stack>
            </>
          )}

          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
            {t('pages.plantInstances.sectionSetup')}
          </Typography>

          <FormRow>
            <FormDateField name="planted_on" control={control} label={t('pages.plantInstances.plantedOn')} required />
            <FormSelectField
              name="current_phase_key"
              control={control}
              label={t('pages.plantInstances.currentPhase')}
              helperText={t('pages.plantInstances.currentPhaseHelper')}
              disabled={phaseOptions.length === 0}
              options={phaseOptions}
            />
          </FormRow>
          {/* ADR-006 E1 (#565) — per-instance cultivation cycle. Optional: leaving it
              on "same as the species" keeps the existing species-driven behaviour, so
              the flow is unchanged when the grower does not decide per plant.
              ADR-006 E6 (#615): only offered for facultative species (can be grown
              annual OR perennial). For any other species the cycle follows the
              species default and an informative caption explains that instead. */}
          {cultivationFlexible ? (
            <FormSelectField
              name="cultivation_cycle_type"
              control={control}
              label={t('pages.plantInstances.cultivationCycle')}
              helperText={t('pages.plantInstances.cultivationCycleHelper')}
              options={[
                { value: '', label: t('pages.plantInstances.cultivationCycleDefault') },
                { value: 'annual', label: t('enums.cycleType.annual') },
                { value: 'biennial', label: t('enums.cycleType.biennial') },
                { value: 'perennial', label: t('enums.cycleType.perennial') },
              ]}
            />
          ) : speciesKey ? (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ display: 'block', mb: 1 }}
              data-testid="cultivation-cycle-fixed-note"
            >
              {t('pages.plantInstances.cultivationCycleFixed')}
            </Typography>
          ) : null}
          <FormTextField name="instance_id" control={control} label={t('pages.plantInstances.instanceId')} required helperText={t('pages.plantInstances.instanceIdHelper')} />
          <SubstrateSelectField
            name="substrate_key"
            control={control}
            label={t('pages.plantInstances.substrate')}
            helperText={t('pages.plantInstances.substrateHelper')}
            substrates={substratesList}
          />

          <LocationAssignmentSection
            control={control}
            sites={sitesList}
            slots={slotsList}
            variant="inline"
          />
          <FormActions onCancel={onClose} loading={saving} saveLabel={t('common.create')} />
        </Form>
      </DialogContent>
    </Dialog>
  );
}
