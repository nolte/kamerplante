// Enums (mirrors src/backend/app/common/enums.py)

/**
 * Data-provenance / ownership marker (REQ-001/REQ-011, mirrors backend
 * `DataOrigin`). Drives read-only / deletion-protection logic (UI-NFR-018).
 */
export type DataOrigin = 'system' | 'enrichment' | 'import' | 'tenant';

export type GrowthHabit =
  | 'herb'
  | 'shrub'
  | 'subshrub'
  | 'tree'
  | 'vine'
  | 'groundcover'
  | 'grass'
  | 'succulent'
  | 'bulb_geophyte'
  | 'fern'
  | 'aquatic'
  | 'epiphyte';
export type HarvestPattern = 'single' | 'continuous' | 'perennial';
export type HarvestedPart =
  | 'fruit'
  | 'seed'
  | 'leaf'
  | 'root'
  | 'tuber'
  | 'bulb'
  | 'flower_bud'
  | 'flower'
  | 'stem'
  | 'whole_plant';
export type ClimactericClass = 'climacteric' | 'non_climacteric' | 'atypical';
export type DtmReference = 'direct_seed' | 'transplant' | 'from_flip';
export type SeedType = 'open_pollinated' | 'f1_hybrid' | 'f2' | 'landrace' | 'clone';
export type FloweringStrategy = 'monocarpic' | 'polycarpic';
export type PhotosynthesisType = 'c3' | 'c4' | 'cam';
export type GrowthDeterminacy = 'determinate' | 'indeterminate' | 'semi_determinate';
export type RootType = 'fibrous' | 'taproot' | 'tuberous' | 'bulbous' | 'corm';
export type PropagationMethod =
  | 'seed'
  | 'cutting'
  | 'leaf_cutting'
  | 'division'
  | 'rhizome_division'
  | 'bulb'
  | 'bulbil'
  | 'tuber'
  | 'offset'
  | 'runner'
  | 'grafting'
  | 'layering'
  | 'air_layering'
  | 'water_propagation'
  | 'tissue_culture'
  | 'spore'
  | 'self_seeding';
export type WoodStage = 'softwood' | 'semi_hardwood' | 'hardwood' | 'herbaceous';
export type PropagationDifficulty = 'easy' | 'moderate' | 'difficult';
export type PhotoperiodType = 'short_day' | 'long_day' | 'day_neutral';
export type CycleType = 'annual' | 'biennial' | 'perennial';
export type StressTolerance = 'low' | 'medium' | 'high';
export type TransitionTriggerType = 'time_based' | 'manual' | 'event_based' | 'conditional';
export type SiteType = 'outdoor' | 'greenhouse' | 'indoor' | 'windowsill' | 'balcony' | 'grow_tent';
export type LightType = 'natural' | 'led' | 'hps' | 'cmh' | 'mixed';
export type IrrigationSystem = 'manual' | 'drip' | 'hydro' | 'mist' | 'nft' | 'ebb_flow';
export type SubstrateType =
  | 'soil'
  | 'coco'
  | 'clay_pebbles'
  | 'perlite'
  | 'living_soil'
  | 'peat'
  | 'rockwool_slab'
  | 'rockwool_plug'
  | 'vermiculite'
  | 'none'
  | 'orchid_bark'
  | 'pon_mineral'
  | 'sphagnum'
  | 'hydro_solution';
export type NutrientDemand = 'light' | 'medium' | 'heavy';
export type RootDepth = 'shallow' | 'medium' | 'deep';
export type FrostTolerance = 'sensitive' | 'moderate' | 'hardy' | 'very_hardy';
export type Suitability = 'yes' | 'limited' | 'no';
export type PollinationType = 'insect' | 'wind' | 'self';
export type WaterRetention = 'low' | 'medium' | 'high';
export type BufferCapacity = 'low' | 'medium' | 'high';
export type Orientation = 'north' | 'south' | 'east' | 'west';
export type PlantTrait =
  | 'disease_resistant'
  | 'pest_resistant'
  | 'high_yield'
  | 'compact'
  | 'drought_tolerant'
  | 'cold_hardy'
  | 'heat_tolerant'
  | 'early_maturing'
  | 'long_season'
  | 'ornamental'
  | 'heirloom'
  | 'hybrid'
  | 'f1';
export type PlantingRunType = 'monoculture' | 'clone';
export type PlantingRunStatus = 'planned' | 'active' | 'harvesting' | 'completed' | 'cancelled';

// REQ-013 §2 — Staffelanbau / succession-plan lifecycle state.
export type SuccessionPlanStatus = 'planned' | 'active' | 'completed' | 'cancelled';
export type DiaryEntryType =
  'observation' | 'problem' | 'milestone' | 'measurement' | 'photo' | 'note';
export type FertilizerType =
  | 'base'
  | 'supplement'
  | 'booster'
  | 'biological'
  | 'ph_adjuster'
  | 'organic'
  | 'silicate'
  | 'calmag';
export type NutrientReleaseSpeed = 'immediate' | 'weeks' | 'months' | 'season_long';
export type NutrientDemandLevel =
  'heavy_feeder' | 'medium_feeder' | 'light_feeder' | 'nitrogen_fixer';
export type PhEffect = 'acidic' | 'alkaline' | 'neutral';
export type ApplicationMethod = 'fertigation' | 'drench' | 'foliar' | 'top_dress' | 'any';
export type Bioavailability = 'immediate' | 'slow_release' | 'microbial_dependent';
export type IncompatibilitySeverity = 'critical' | 'warning' | 'minor';
export type PhaseName =
  'germination' | 'seedling' | 'vegetative' | 'flowering' | 'flushing' | 'dormancy' | 'harvest';
export type ActivityCategory =
  | 'training_hst'
  | 'training_lst'
  | 'pruning'
  | 'ausgeizen'
  | 'transplant'
  | 'harvest_prep'
  | 'propagation'
  | 'general';
export type StressLevel = 'none' | 'low' | 'medium' | 'high';

// Pagination

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}

// Error response (NFR-006)

export interface ApiErrorResponse {
  error_id: string;
  error_code: string;
  message: string;
  details: ApiErrorDetail[];
  timestamp: string;
  path: string;
  method: string;
}

export interface ApiErrorDetail {
  field: string;
  reason: string;
  code: string;
}

// Botanical Families

export interface PhRange {
  min_ph: number;
  max_ph: number;
}

export interface BotanicalFamily {
  key: string;
  name: string;
  common_name_de: string;
  common_name_en: string;
  order: string | null;
  description: string;
  typical_nutrient_demand: NutrientDemand;
  nitrogen_fixing: boolean;
  typical_root_depth: RootDepth;
  soil_ph_preference: PhRange | null;
  frost_tolerance: FrostTolerance;
  typical_growth_forms: GrowthHabit[];
  common_pests: string[];
  common_diseases: string[];
  pollination_type: PollinationType[];
  rotation_category: string;
  species_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface BotanicalFamilyCreate {
  name: string;
  common_name_de?: string;
  common_name_en?: string;
  order?: string | null;
  description?: string;
  typical_nutrient_demand?: NutrientDemand;
  nitrogen_fixing?: boolean;
  typical_root_depth?: RootDepth;
  soil_ph_preference?: PhRange | null;
  frost_tolerance?: FrostTolerance;
  typical_growth_forms?: GrowthHabit[];
  common_pests?: string[];
  common_diseases?: string[];
  pollination_type?: PollinationType[];
  rotation_category?: string;
}

// Watering Guide (embedded on Species/Cultivar)

export interface SeasonalWateringAdjustment {
  months: number[];
  interval_days: number;
  volume_ml_min: number;
  volume_ml_max: number;
  label: string;
}

export interface WateringGuide {
  interval_days: number;
  volume_ml_min: number;
  volume_ml_max: number;
  watering_method: WateringMethod;
  water_quality_hint: string | null;
  practical_tip: string | null;
  seasonal_adjustments: SeasonalWateringAdjustment[];
}

// Species

export interface GrowingPeriod {
  label: string;
  sowing_indoor_weeks_before_last_frost: number | null;
  sowing_outdoor_after_last_frost_days: number | null;
  direct_sow_months: number[];
  growth_months: number[];
  harvest_months: number[];
  bloom_months: number[];
  harvest_from_year: number | null;
  bloom_from_year: number | null;
}

export interface PropagationConfig {
  method: PropagationMethod;
  months: number[];
  wood_stage?: WoodStage | null;
  difficulty?: PropagationDifficulty | null;
  notes?: string | null;
}

/**
 * Canonical toxicity severity (REQ-001 — `Toxicity.severity`).
 *
 * Distinct from the flat legacy `Species.toxicity_severity` passthrough
 * (low/moderate/high), which uses a different scale and is intentionally not
 * mapped onto this enum.
 */
export type ToxicitySeverity = 'none' | 'mild' | 'moderate' | 'severe';

/**
 * Structured toxicity profile of a species (REQ-001 — pet/child safety).
 * Rendered level-independently by the detail page so the warning is never
 * hidden behind an expertise-level gate.
 */
export interface Toxicity {
  is_toxic_cats: boolean;
  is_toxic_dogs: boolean;
  is_toxic_children: boolean;
  toxic_parts: string[];
  toxic_compounds: string[];
  severity: ToxicitySeverity | null;
}

export interface Species {
  key: string;
  origin?: DataOrigin;
  scientific_name: string;
  common_names: string[];
  family_key: string | null;
  family_name: string | null;
  genus: string;
  hardiness_zones: string[];
  native_habitat: string;
  growth_habit: GrowthHabit;
  /** REQ-001 v4.2 — photosynthesis pathway (WUE/transpiration modifier). Optional
   * for backward compatibility with pre-field API responses. */
  photosynthesis_type?: PhotosynthesisType | null;
  root_type: RootType;
  allelopathy_score: number;
  base_temp: number;
  synonyms: string[];
  taxonomic_authority: string;
  taxonomic_status: string;
  description: string;
  sowing_indoor_weeks_before_last_frost: number | null;
  sowing_outdoor_after_last_frost_days: number | null;
  direct_sow_months: number[];
  harvest_months: number[];
  bloom_months: number[];
  harvest_from_year: number | null;
  bloom_from_year: number | null;
  frost_sensitivity: FrostTolerance | null;
  plant_category: string | null;
  harvest_pattern: HarvestPattern | null;
  harvested_part: HarvestedPart | null;
  climacteric: ClimactericClass | null;
  toxicity?: Toxicity | null;
  propagation_configs: PropagationConfig[];
  allows_harvest: boolean;
  growing_periods: GrowingPeriod[];
  container_suitable: Suitability | null;
  recommended_container_volume_l: string | null;
  min_container_depth_cm: number | null;
  mature_height_cm: string | null;
  mature_width_cm: string | null;
  spacing_cm: string | null;
  indoor_suitable: Suitability | null;
  balcony_suitable: Suitability | null;
  greenhouse_recommended: boolean;
  support_required: boolean;
  watering_guide: WateringGuide | null;
  default_nutrient_plan_key: string | null;
  /**
   * ADR-006 E6: the species can be grown facultatively as annual OR perennial.
   * Gates whether the plant-create flow offers the per-instance cultivation-cycle
   * choice. Optional for backward compatibility with pre-flag API responses.
   */
  cultivation_flexible?: boolean;
  representative_image_url: string | null;
  representative_image_attribution: string | null;
  representative_image_license: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/** A single reference image for a species (REQ-029-A). External CC0/CC-BY URL. */
export interface ReferenceImage {
  source_url: string;
  license?: string | null;
  attribution?: string | null;
  organ?: string | null;
  source?: string | null;
}

/** Reference-image gallery response for a species (REQ-029-A). */
export interface SpeciesReferenceImages {
  species_key: string;
  count: number;
  images: ReferenceImage[];
}

/** Reason an admin can give when deselecting a reference image (REQ-029-A). */
export type ReferenceExclusionReason =
  'blurry' | 'wrong_organ' | 'wrong_species' | 'duplicate' | 'irrelevant' | 'manual';

/** One reference image in the admin curation view (includes deselected ones). */
export interface CurationImage extends ReferenceImage {
  id: number;
  is_active: boolean;
  exclusion_reason?: string | null;
}

/** Admin curation listing for a species (all images, incl. deselected). */
export interface CurationImageList {
  species_key: string;
  count: number;
  active_count: number;
  images: CurationImage[];
}

/** Payload to deselect or re-include a reference image. */
export interface SetImageActiveRequest {
  is_active: boolean;
  reason?: ReferenceExclusionReason | null;
}

/** Result of toggling a reference image's active flag. */
export interface SetImageActiveResponse {
  species_key: string;
  id: number;
  is_active: boolean;
}

export interface SpeciesCreate {
  scientific_name: string;
  common_names?: string[];
  family_key?: string | null;
  genus?: string;
  hardiness_zones?: string[];
  native_habitat?: string;
  growth_habit?: GrowthHabit;
  photosynthesis_type?: PhotosynthesisType | null;
  root_type?: RootType;
  allelopathy_score?: number;
  base_temp?: number;
  synonyms?: string[];
  taxonomic_authority?: string;
  taxonomic_status?: string;
  description?: string;
  sowing_indoor_weeks_before_last_frost?: number | null;
  sowing_outdoor_after_last_frost_days?: number | null;
  direct_sow_months?: number[];
  harvest_months?: number[];
  bloom_months?: number[];
  harvest_from_year?: number | null;
  bloom_from_year?: number | null;
  frost_sensitivity?: FrostTolerance | null;
  plant_category?: string | null;
  harvest_pattern?: HarvestPattern | null;
  harvested_part?: HarvestedPart | null;
  climacteric?: ClimactericClass | null;
  propagation_configs?: PropagationConfig[];
  allows_harvest?: boolean;
  growing_periods?: GrowingPeriod[];
  container_suitable?: Suitability | null;
  recommended_container_volume_l?: string | null;
  min_container_depth_cm?: number | null;
  mature_height_cm?: string | null;
  mature_width_cm?: string | null;
  spacing_cm?: string | null;
  indoor_suitable?: Suitability | null;
  balcony_suitable?: Suitability | null;
  greenhouse_recommended?: boolean;
  support_required?: boolean;
  watering_guide?: WateringGuide | null;
  default_nutrient_plan_key?: string | null;
}

// Cultivars

export interface Cultivar {
  key: string;
  origin?: DataOrigin;
  name: string;
  species_key: string;
  breeder: string | null;
  breeding_year: number | null;
  traits: PlantTrait[];
  patent_status: string;
  seed_type: SeedType | null;
  days_to_maturity: number | null;
  dtm_reference: DtmReference | null;
  bearing_start_year_min: number | null;
  bearing_start_year_max: number | null;
  disease_resistances: string[];
  phase_watering_overrides: Record<string, number> | null;
  created_at: string | null;
  updated_at: string | null;
}

// Mirrors the backend `CultivarCreate`, which carries no `species_key` (#1114):
// the parent species is the URL path segment on every cultivar route.
export interface CultivarCreate {
  name: string;
  breeder?: string | null;
  breeding_year?: number | null;
  traits?: PlantTrait[];
  patent_status?: string;
  seed_type?: SeedType | null;
  days_to_maturity?: number | null;
  dtm_reference?: DtmReference | null;
  bearing_start_year_min?: number | null;
  bearing_start_year_max?: number | null;
  disease_resistances?: string[];
  phase_watering_overrides?: Record<string, number> | null;
}

// Sites

// Water config types

export interface TapWaterProfile {
  ec_ms: number;
  ph: number;
  alkalinity_ppm: number;
  gh_ppm: number;
  calcium_ppm: number;
  magnesium_ppm: number;
  chlorine_ppm: number;
  chloramine_ppm: number;
  measurement_date: string | null;
  source_note: string | null;
}

export interface RoWaterProfile {
  ec_ms: number;
  ph: number;
}

export interface SiteWaterConfig {
  has_ro_system: boolean;
  tap_water_profile?: TapWaterProfile | null;
  ro_water_profile?: RoWaterProfile | null;
}

export interface WaterSourceWarning {
  code: string;
  message: string;
  severity: string;
}

export type HardinessZoneSource = 'manual' | 'derived_gps' | 'derived_postal' | 'frostline_us';

export interface Site {
  key: string;
  name: string;
  type: SiteType;
  gps_coordinates: [number, number] | null;
  climate_zone: string;
  total_area_m2: number;
  timezone: string;
  water_config?: SiteWaterConfig | null;
  water_config_warnings?: WaterSourceWarning[];
  last_frost_date_avg: string | null;
  first_frost_date_avg: string | null;
  eisheilige_date: string | null;
  hardiness_zone?: string | null;
  hardiness_zone_source?: HardinessZoneSource;
  hardiness_zone_resolved_at?: string | null;
  mean_annual_minimum_c?: number | null;
  created_at: string | null;
  updated_at: string | null;
}

/** One canonical USDA hardiness zone (global reference data). */
export interface HardinessZoneCatalogEntry {
  zone: string;
  zone_number: number;
  subzone: string;
  temp_min_c: number;
  temp_max_c: number;
  temp_min_f: number;
  temp_max_f: number;
  description_de: string;
  representative_regions_de: string[];
  typical_last_frost_md?: string | null;
  typical_first_frost_md?: string | null;
}

/** A site's resolved hardiness zone plus the matching catalog entry (REQ-039/041). */
export interface SiteHardinessResponse {
  site_key: string;
  hardiness_zone: string | null;
  hardiness_zone_source: HardinessZoneSource;
  hardiness_zone_resolved_at: string | null;
  mean_annual_minimum_c: number | null;
  last_frost_date_avg: string | null;
  first_frost_date_avg: string | null;
  zone: HardinessZoneCatalogEntry | null;
}

export interface SiteCreate {
  name: string;
  type?: SiteType;
  gps_coordinates?: [number, number] | null;
  climate_zone?: string;
  total_area_m2?: number;
  timezone?: string;
  water_config?: SiteWaterConfig | null;
  last_frost_date_avg?: string | null;
  first_frost_date_avg?: string | null;
  eisheilige_date?: string | null;
}

// Locations

export interface Location {
  key: string;
  name: string;
  site_key: string;
  parent_location_key: string | null;
  location_type_key: string;
  depth: number;
  path: string;
  area_m2: number;
  orientation: Orientation | null;
  light_type: LightType;
  irrigation_system: IrrigationSystem;
  dimensions: [number, number, number];
  lights_on: string | null;
  lights_off: string | null;
  use_dynamic_sunrise: boolean;
  frost_exposed: boolean | null;
  tank_key: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface LocationCreate {
  name: string;
  site_key: string;
  parent_location_key?: string | null;
  location_type_key?: string;
  area_m2: number;
  orientation?: Orientation | null;
  light_type?: LightType;
  irrigation_system?: IrrigationSystem;
  dimensions?: [number, number, number];
  lights_on?: string | null;
  lights_off?: string | null;
  use_dynamic_sunrise?: boolean;
  frost_exposed?: boolean | null;
  tank_key?: string | null;
}

export interface LocationTreeNode {
  key: string;
  name: string;
  location_type_key: string;
  depth: number;
  parent_location_key: string | null;
  slot_count: number;
  active_plant_count: number;
  tank_name: string | null;
  children: LocationTreeNode[];
}

export interface LocationType {
  key: string;
  name: string;
  name_en: string | null;
  icon: string | null;
  is_indoor: boolean;
  is_system: boolean;
  sort_order: number;
  description: string | null;
}

// Slots

export interface Slot {
  key: string;
  slot_id: string;
  location_key: string;
  position: [number, number];
  capacity_plants: number;
  currently_occupied: boolean;
  last_sanitization: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface SlotCreate {
  slot_id: string;
  location_key: string;
  position?: [number, number];
  capacity_plants?: number;
}

// Substrates

export interface MixComponent {
  substrate_key: string;
  fraction: number;
}

export interface Substrate {
  key: string;
  type: SubstrateType;
  brand: string | null;
  name_de: string;
  name_en: string;
  is_mix: boolean;
  mix_components: MixComponent[];
  ph_base: number;
  ec_base_ms: number;
  water_retention: WaterRetention;
  /**
   * Air-filled porosity at container capacity, or `null` where the field does not
   * apply — `Hydrokultur (kein Substrat)` has no pore space to describe (#1175).
   * `null` is "not applicable", never "unknown" and never zero.
   */
  air_porosity_percent: number | null;
  composition: Record<string, number>;
  /**
   * Amendments the product contains, named without a quantity (#1175). Lime and
   * trace elements are dosed at single-digit kg/m³ and cannot sit in the
   * normalised `composition` vector, where they read as real volume proportions.
   */
  additives: string[];
  /** A soil conditioner rather than a growing medium — not something to plant in. */
  is_amendment: boolean;
  buffer_capacity: BufferCapacity;
  reusable: boolean;
  max_reuse_cycles: number;
  water_holding_capacity_percent: number | null;
  easily_available_water_percent: number | null;
  cec_meq_per_100cm3: number | null;
  particle_size_mm: number | null;
  bulk_density_g_per_l: number | null;
  irrigation_strategy: IrrigationStrategy | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface SubstrateMixRequest {
  name_de: string;
  name_en: string;
  components: MixComponent[];
}

export interface SubstrateCreate {
  type?: SubstrateType;
  brand?: string | null;
  name_de?: string;
  name_en?: string;
  ph_base?: number;
  ec_base_ms?: number;
  water_retention?: WaterRetention;
  air_porosity_percent?: number | null;
  composition?: Record<string, number>;
  additives?: string[];
  is_amendment?: boolean;
  buffer_capacity?: BufferCapacity;
  reusable?: boolean;
  max_reuse_cycles?: number;
}

// Batches

export interface Batch {
  key: string;
  batch_id: string;
  substrate_key: string;
  volume_liters: number;
  mixed_on: string;
  last_amended: string | null;
  cycles_used: number;
  ph_current: number | null;
  ec_current_ms: number | null;
  temperature_c: number | null;
  ph_history: number[];
  ec_history: number[];
  created_at: string | null;
  updated_at: string | null;
}

export interface BatchCreate {
  batch_id: string;
  substrate_key: string;
  volume_liters: number;
  mixed_on: string;
}

export interface ReusabilityResponse {
  can_reuse: boolean;
  treatments: string[];
}

// Plant Instances

/** Denormalized species fields embedded in plant responses for readable labels. */
export interface PlantSpeciesSummary {
  scientific_name: string;
  common_names: string[];
}

/** Denormalized cultivar fields embedded in plant responses for readable labels. */
export interface PlantCultivarSummary {
  name: string;
}

export interface PlantInstance {
  key: string;
  instance_id: string;
  species_key: string;
  cultivar_key: string | null;
  site_key: string | null;
  location_key: string | null;
  slot_key: string | null;
  substrate_batch_key: string | null;
  substrate_key: string | null;
  plant_name: string | null;
  planted_on: string;
  removed_on: string | null;
  termination_type: TerminationType | null;
  termination_cause: TerminationCause | null;
  current_phase: string;
  current_phase_key: string | null;
  current_phase_started_at: string | null;
  container_volume_liters: number | null;
  substrate_type_override: SubstrateType | null;
  /**
   * Per-instance cultivation cycle override (ADR-006 E1, #565). null/absent = "same as
   * the species". The practised cycle axis (#297): overrides the species default for the
   * season/overwintering and cycle-restart decisions; the botanical cycle stays species-fixed.
   */
  cultivation_cycle_type?: CycleType | null;
  species: PlantSpeciesSummary | null;
  cultivar: PlantCultivarSummary | null;
  /** Key of the mother instance this pup descended from via clonal continuation (D10, REQ-017). */
  mother_key: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/** How a plant instance's lifecycle ended (REQ-003 E5). */
export type TerminationType = 'harvested' | 'senesced' | 'died' | 'cancelled';

/** Cause of an unplanned loss — only valid together with type='died' (REQ-003 E5). */
export type TerminationCause =
  | 'disease'
  | 'pest'
  | 'frost'
  | 'heat'
  | 'drought'
  | 'waterlogging'
  | 'neglect'
  | 'mechanical'
  | 'unknown';

/** Optional body for POST /{key}/remove — classifies how the lifecycle ended. */
export interface RemovePlantRequest {
  termination_type?: TerminationType | null;
  termination_cause?: TerminationCause | null;
}

export interface TerminationTypeCount {
  termination_type: TerminationType;
  count: number;
}

export interface TerminationCauseCount {
  termination_cause: TerminationCause;
  count: number;
}

export interface PhaseLossCount {
  phase_name: string;
  count: number;
}

/** Survival-rate / failure-cause analytics for the tenant (REQ-003 G1). */
export interface SurvivalStats {
  total: number;
  terminated: number;
  active: number;
  died: number;
  survived: number;
  survival_rate: number;
  by_termination_type: TerminationTypeCount[];
  by_termination_cause: TerminationCauseCount[];
  loss_by_phase: PhaseLossCount[];
}

export interface PlantInstanceCreate {
  instance_id: string;
  species_key: string;
  cultivar_key?: string | null;
  site_key?: string | null;
  location_key?: string | null;
  slot_key?: string | null;
  substrate_batch_key?: string | null;
  substrate_key?: string | null;
  plant_name?: string | null;
  planted_on: string;
  current_phase_key?: string | null;
  container_volume_liters?: number | null;
  substrate_type_override?: SubstrateType | null;
  /** Per-instance cultivation cycle override (ADR-006 E1, #565). null/omitted = "same as the species". */
  cultivation_cycle_type?: CycleType | null;
}

export interface ValidatePlantingResponse {
  valid: boolean;
  warnings: string[];
  benefits: string[];
}

// Phase Control

export interface CurrentPhaseResponse {
  phase: string;
  phase_key: string | null;
  days_in_phase: number;
  next_phase: string | null;
  cycle_type: CycleType | null;
  cycle_number: number;
  has_harvest_phase: boolean;
}

export interface PhaseHistoryEntry {
  key: string;
  phase_name: string;
  entered_at: string;
  exited_at: string | null;
  actual_duration_days: number | null;
  transition_reason: string;
  performance_score: number | null;
}

export interface TransitionRequest {
  target_phase_key: string;
  reason?: string;
  force?: boolean;
}

// Growth Phases

export interface GrowthPhase {
  key: string;
  name: string;
  display_name: string;
  description: string;
  lifecycle_key: string;
  typical_duration_days: number;
  sequence_order: number;
  is_terminal: boolean;
  allows_harvest: boolean;
  stress_tolerance: StressTolerance;
  watering_interval_days: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface GrowthPhaseCreate {
  name: string;
  display_name?: string;
  description?: string;
  lifecycle_key: string;
  typical_duration_days: number;
  sequence_order: number;
  is_terminal?: boolean;
  allows_harvest?: boolean;
  stress_tolerance?: StressTolerance;
  watering_interval_days?: number | null;
}

// Lifecycle Config

export interface LifecycleConfig {
  key: string;
  species_key: string;
  cycle_type: CycleType;
  cultivation_cycle_type: CycleType | null;
  flowering_strategy: FloweringStrategy | null;
  /** REQ-003 E4 — growth determinacy (orthogonal to lifespan/flowering). Optional
   * for backward compatibility with pre-field API responses. */
  growth_determinacy?: GrowthDeterminacy | null;
  typical_lifespan_years: number | null;
  dormancy_required: boolean;
  vernalization_required: boolean;
  vernalization_min_days: number | null;
  photoperiod_type: PhotoperiodType;
  critical_day_length_hours: number | null;
  phase_sequence_key: string | null;
  /** Derived read-only flag — species is cultivated as a (tender) annual
   * (cultivation_cycle_type === 'annual' while the botanical cycle_type is not).
   * Computed server-side; never sent on create/update. */
  grown_as_annual: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface LifecycleConfigCreate {
  species_key: string;
  cycle_type?: CycleType;
  cultivation_cycle_type?: CycleType | null;
  flowering_strategy?: FloweringStrategy | null;
  growth_determinacy?: GrowthDeterminacy | null;
  typical_lifespan_years?: number | null;
  dormancy_required?: boolean;
  vernalization_required?: boolean;
  vernalization_min_days?: number | null;
  photoperiod_type?: PhotoperiodType;
  critical_day_length_hours?: number | null;
}

// Profiles

export interface RequirementProfile {
  key: string;
  phase_key: string;
  light_ppfd_target: number;
  photoperiod_hours: number;
  light_spectrum: Record<string, number>;
  temperature_day_c: number;
  temperature_night_c: number;
  humidity_day_percent: number;
  humidity_night_percent: number;
  vpd_target_kpa: number;
  co2_ppm: number | null;
  irrigation_frequency_days: number;
  irrigation_volume_ml_per_plant: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface RequirementProfileCreate {
  phase_key: string;
  light_ppfd_target?: number;
  photoperiod_hours?: number;
  light_spectrum?: Record<string, number>;
  temperature_day_c?: number;
  temperature_night_c?: number;
  humidity_day_percent?: number;
  humidity_night_percent?: number;
  vpd_target_kpa?: number;
  co2_ppm?: number | null;
  irrigation_frequency_days?: number;
  irrigation_volume_ml_per_plant?: number;
}

export interface NutrientProfile {
  key: string;
  phase_key: string;
  npk_ratio: [number, number, number];
  target_ec_ms: number;
  target_ph: number;
  calcium_ppm: number | null;
  magnesium_ppm: number | null;
  micro_nutrients: Record<string, number>;
  /** REQ-003 E8: whether this phase is fed at all (false for flush/rest — 0:0:0). */
  feed?: boolean;
  /** REQ-003 E8: whether the phase target pH keeps micronutrients available (pH gating). */
  micros_available?: boolean;
  /** Human-readable pH / micronutrient-availability guidance from the resolver. */
  ph_note?: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface NutrientProfileCreate {
  phase_key: string;
  npk_ratio?: [number, number, number];
  target_ec_ms?: number;
  target_ph?: number;
  calcium_ppm?: number | null;
  magnesium_ppm?: number | null;
  micro_nutrients?: Record<string, number>;
}

// Companion Planting

export interface CompatibleSpecies {
  species_key: string;
  scientific_name: string | null;
  /** Language-mixed common-name list (DE first by convention); UI leads with [0]. */
  common_names: string[];
  score: number;
}

export interface IncompatibleSpecies {
  species_key: string;
  scientific_name: string | null;
  /** Language-mixed common-name list (DE first by convention); UI leads with [0]. */
  common_names: string[];
  reason: string;
}

export interface SpeciesCompanionCounts {
  compatible: number;
  incompatible: number;
}

/** Whole-catalogue aggregate keyed by species_key (GET /companion-planting/counts). */
export type CompanionCountsMap = Record<string, SpeciesCompanionCounts>;

export interface CompatibilitySet {
  from_species_key: string;
  to_species_key: string;
  score?: number;
}

export interface IncompatibilitySet {
  from_species_key: string;
  to_species_key: string;
  reason?: string;
}

// Crop Rotation

export interface RotationSuccessor {
  family_key: string;
  name: string | null;
  /** German family common name (e.g. "Nachtschattengewächse"); UI leads with it. */
  common_name_de: string;
  common_name_en: string;
  /** Raw rotation-category code (e.g. "legume"); UI maps it to a translated label. */
  rotation_category: string;
  wait_years: number;
  benefit_score: number;
  benefit_reason: string;
}

export interface RotationSuccessorSet {
  from_family_key: string;
  to_family_key: string;
  wait_years?: number;
  benefit_score?: number;
  benefit_reason?: string;
}

/** Whole-catalogue aggregate keyed by family_key (GET /crop-rotation/counts):
 *  the number of curated rotation successors per botanical family. */
export type RotationCountsMap = Record<string, number>;

// Family Relationships

export interface PestRisk {
  family_key: string;
  name: string | null;
  shared_pests: string[];
  shared_diseases: string[];
  risk_level: string;
}

export interface FamilyCompatible {
  family_key: string;
  name: string | null;
  benefit_type: string;
  compatibility_score: number;
  notes: string;
}

export interface FamilyIncompatible {
  family_key: string;
  name: string | null;
  reason: string;
  severity: string;
}

// Companion Planting Recommendations

export interface CompanionRecommendation {
  species_key: string;
  scientific_name: string | null;
  score: number;
  match_level: 'species' | 'family';
  benefit_type?: string;
}

export interface CompanionRecommendationResponse {
  matches: CompanionRecommendation[];
  match_level: 'species' | 'family';
}

// Vernalization

export interface VernalizationRequest {
  cold_days_accumulated: number;
  required_min_days: number;
}

export interface VernalizationResponse {
  progress_percent: number;
  days_remaining: number;
  is_complete: boolean;
}

// Calculations

export interface VPDRequest {
  temp_c: number;
  humidity_percent: number;
  phase?: string;
}

export interface VPDResponse {
  vpd_kpa: number;
  status: string;
  recommendation: string;
}

export interface GDDRequest {
  daily_temps: [number, number][];
  base_temp_c?: number;
}

export interface GDDResponse {
  accumulated_gdd: number;
  days_counted: number;
}

export interface PhotoperiodTransitionRequest {
  current_hours: number;
  target_hours: number;
  transition_days?: number;
  ppfd?: number;
  lights_on_time?: string;
}

export interface PhotoperiodScheduleEntry {
  day: number;
  photoperiod_hours: number;
  lights_on: string;
  lights_off: string;
  dli: number;
}

export interface SunTimesRequest {
  latitude: number;
  longitude: number;
  date: string;
  timezone?: string;
}

export interface SunTimesResponse {
  date: string;
  sunrise: string;
  sunset: string;
  dawn: string;
  dusk: string;
  day_length_hours: number;
}

export interface SlotCapacityRequest {
  area_m2: number;
  plant_spacing_cm: number;
}

export interface SlotCapacityResponse {
  max_capacity: number;
  optimal_range: [number, number];
  plants_per_m2: number;
}

// Planting Runs (REQ-013)

export interface PlantingRunEntry {
  key: string;
  run_key: string;
  species_key: string;
  cultivar_key: string | null;
  quantity: number;
  id_prefix: string;
  spacing_cm: number | null;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PlantingRunEntryCreate {
  species_key: string;
  cultivar_key?: string | null;
  quantity: number;
  id_prefix: string;
  spacing_cm?: number | null;
  notes?: string | null;
}

/**
 * REQ-050 §2.2 — analysis state of a single diary entry.
 *
 * `none` is a real, stored value; entries written before REQ-050 carry no
 * attribute at all and the backend reads those as `none` (AK-26), so the client
 * never has to treat "missing" as a sixth case.
 */
export type DiaryAnalysisState =
  | 'none'
  | 'requested'
  | 'in_progress'
  | 'completed'
  | 'failed';

/** REQ-050 §5 — one finding of an AI analysis. */
export interface DiaryFinding {
  label: string;
  /** Model confidence, 0.0–1.0. Never rendered as a bare percentage (AK-30). */
  confidence: number;
  rationale: string;
}

/** REQ-050 §5 — the single, most recent analysis result stored on an entry. */
export interface DiaryAnalysis {
  summary: string;
  findings: DiaryFinding[];
  recommended_actions: string[];
  /** Which photos actually went into the analysis (subset of `photo_refs`). */
  analyzed_photo_ids: string[];
  model: string;
  recipe_version: string;
  analyzed_at: string;
  /** Set server-side, never by the agent (§4.5). Always displayed (AK-20). */
  disclaimer: string;
}

/**
 * REQ-013 §2.3a — which level of the REQ-005 fallback chain answered a reading.
 *
 * Not the same question as `source`: `origin` says how *close to the plant* the
 * value was measured, `source` says how it was produced. There is no `slot`
 * level — a sensor cannot be attached to a slot.
 */
export type DiaryEnvironmentOrigin = 'location' | 'site' | 'weather';

/**
 * REQ-013 §2.3a — what an empty `environment` list *means*.
 *
 * The list alone is ambiguous, and the four empty cases are different
 * statements: only `no_source` says something about the garden.
 */
export type DiaryEnvironmentStatus =
  /** No capture ran — an entry from before the feature, or the switch is off. */
  | 'not_attempted'
  /** The author declined the snapshot when creating the entry. */
  | 'opted_out'
  /** The chain ran cleanly and produced at least one reading. */
  | 'captured'
  /** The chain ran cleanly; nothing measures this plant. */
  | 'no_source'
  /** The chain was cut short. A non-empty list here is a *partial* snapshot. */
  | 'unavailable';

/**
 * REQ-013 §2.3a — one machine-read value of an entry's environment snapshot.
 *
 * Read-only everywhere. Editing an automatic value is deliberately not offered:
 * a corrected sensor reading is a manual measurement and belongs in
 * `measurements`, which is the field that carries no provenance precisely
 * because a human wrote it.
 */
export interface DiaryEnvironmentReading {
  metric_type: string;
  value: number;
  unit: string | null;
  /** REQ-005 §2 provenance, or the weather adapter's name for `origin: weather`. */
  source: string;
  /** When the reading was **measured** — regularly older than `created_at`. */
  measured_at: string;
  sensor_key: string | null;
  origin: DiaryEnvironmentOrigin;
}

/** Response of `GET /plant-instances/{key}/environment` — the create preview. */
export interface PlantEnvironmentPreview {
  plant_key: string;
  readings: DiaryEnvironmentReading[];
  captured_at: string | null;
  environment_status: DiaryEnvironmentStatus;
}

/**
 * A plant diary entry as returned by the standalone diary endpoints
 * (`/t/{slug}/plant-instances/{key}/diary`, REQ-013 §4.7 + REQ-050 §5).
 *
 * Mirrors `DiaryEntryResponse` in
 * `src/backend/app/api/v1/planting_runs/diary_schemas.py` field for field.
 * The previous shape of this (never-used) interface carried a `tenant_key` the
 * response does not expose, made `created_at`/`updated_at` nullable although the
 * response requires them, and predated all eight REQ-050 analysis fields.
 */
export interface PlantDiaryEntry {
  key: string;
  plant_key: string;
  entry_type: DiaryEntryType;
  title: string | null;
  text: string;
  photo_refs: string[];
  tags: string[];
  measurements: Record<string, unknown> | null;
  created_by: string;
  created_at: string;
  updated_at: string;

  /**
   * REQ-013 §2.3a — the machine-read conditions at the moment the entry was
   * created, resolved server-side from the plant's location.
   *
   * Strictly separate from {@link PlantDiaryEntry.measurements}: that dict is
   * the grower's own, free-form and unprovenanced. Merging the two would make it
   * impossible to tell afterwards what a human measured and what a machine
   * reported — which is the only thing that makes either readable as evidence.
   */
  environment: DiaryEnvironmentReading[];
  /** When the capture ran. `null` when none ran (`not_attempted`/`opted_out`). */
  environment_captured_at: string | null;
  /** What an empty `environment` means — never derive it from the list length. */
  environment_status: DiaryEnvironmentStatus;

  // REQ-050 §5 — read-only projection of the analysis state machine. None of
  // these may be sent back through create/update; every transition has its own
  // guarded endpoint.

  /**
   * The state to **display**, corrected server-side: an entry whose agent lease
   * ran out reads as `requested`, not `in_progress`, because it is back in the
   * work queue (AK-06). The same correction the overview row carries — the two
   * views of one entry answer identically, so the client never re-derives it
   * from `analysis_lease_expires_at`.
   */
  analysis_state: DiaryAnalysisState;
  analysis_requested_at: string | null;
  analysis_requested_by: string | null;
  analysis_claimed_at: string | null;
  analysis_claimed_by: string | null;
  analysis_lease_expires_at: string | null;
  analysis: DiaryAnalysis | null;
  analysis_error: string | null;

  /**
   * §7.2 evaluated server-side from role, authorship, consent and operating
   * mode (AK-18a) — for the user of *this* request and *this* entry, so one
   * listing legitimately mixes `true` and `false` rows.
   *
   * A display aid only: marking re-evaluates the identical rule and answers 403
   * regardless of what the client believed.
   */
  can_request_analysis: boolean;
}

/** POST body for a new diary entry (`DiaryEntryCreateRequest`). */
export interface PlantDiaryEntryCreate {
  entry_type: DiaryEntryType;
  title?: string | null;
  text: string;
  photo_refs?: string[];
  tags?: string[];
  measurements?: Record<string, unknown> | null;
  /**
   * REQ-013 §2.3a — whether the server should capture the environment snapshot.
   * Defaults to `true` server-side.
   *
   * The readings themselves are **not** part of this body and never will be: a
   * value the client can write is a value the client can invent, and this one is
   * meant to be evidence. This flag says whether to look, not what to store.
   */
  capture_environment?: boolean;
}

/** PUT body for an existing diary entry (`DiaryEntryUpdateRequest`). */
export interface PlantDiaryEntryUpdate {
  entry_type?: DiaryEntryType;
  title?: string | null;
  text?: string;
  photo_refs?: string[];
  tags?: string[];
  measurements?: Record<string, unknown> | null;
}

/**
 * REQ-051 §6.2 — one row of the tenant-wide diary overview.
 *
 * Deliberately slimmer than {@link PlantDiaryEntry}: it carries the analysis
 * *summary* but never `findings` or `recommended_actions` (AK-18). Both views
 * publish `can_request_analysis` and the lease-corrected `analysis_state`, from
 * the same server-side functions — a row and a full entry never disagree about
 * the same document.
 */
export interface DiaryOverviewItem {
  key: string;
  created_at: string | null;
  entry_type: DiaryEntryType;
  title: string | null;
  /** Server-side truncated beginning of `text` (max 200 chars). */
  excerpt: string;
  tags: string[];

  plant_key: string;
  plant_name: string | null;
  instance_id: string;
  species_name: string | null;

  photo_count: number;
  preview_photo_id: string | null;

  /**
   * The state to *display*: an entry whose agent lease ran out reads as
   * `requested` here even though it is stored as `in_progress`.
   */
  analysis_state: DiaryAnalysisState;
  analysis_summary: string | null;
  analysis_error: string | null;
  /**
   * When an agent claimed the entry — the *start* of the lease, not the end of
   * the run (`analyzed_at`). It belongs to the run this row's `analysis_state`
   * describes: a row whose lease ran out reads as `requested` and carries
   * `null` here, so a moment of claiming never appears next to "waiting for
   * analysis". The full lease (`analysis_claimed_by`,
   * `analysis_lease_expires_at`) is on the single-entry read.
   */
  analysis_claimed_at: string | null;
  analyzed_at: string | null;

  /**
   * §7.2 evaluated server-side from role, authorship, consent and operating
   * mode (AK-18a). A display aid only — marking re-evaluates the same rule and
   * answers 403 regardless of what the client believed.
   */
  can_request_analysis: boolean;
}

/** A page of the tenant-wide diary overview (REQ-051 §6.2). */
export interface DiaryOverviewResponse {
  items: DiaryOverviewItem[];
  /** Matches across all pages, independent of `limit`. */
  total: number;
  limit: number;
  offset: number;
}

export interface PhaseSummary {
  dominant_phase: string | null;
  dominant_phase_count: number;
  total_plant_count: number;
  all_phases: Record<string, number>;
}

export interface PhaseTimelineEntry {
  phase_key: string;
  phase_name: string;
  display_name: string;
  description?: string;
  sequence_order: number;
  typical_duration_days: number;
  status: 'completed' | 'current' | 'projected';
  actual_entered_at: string | null;
  actual_exited_at: string | null;
  actual_duration_days: number | null;
  projected_start: string | null;
  projected_end: string | null;
}

export interface SpeciesPhaseTimeline {
  species_key: string;
  species_name: string | null;
  lifecycle_key: string;
  cycle_type: CycleType | null;
  plant_count: number;
  phases: PhaseTimelineEntry[];
}

export interface PhaseHistoryDateUpdate {
  entered_at?: string;
  exited_at?: string;
}

export interface PlantingRun {
  key: string;
  name: string;
  run_type: PlantingRunType;
  status: PlantingRunStatus;
  planned_quantity: number;
  actual_quantity: number;
  current_phase_key: string | null;
  current_phase_started_at: string | null;
  lifecycle_config_key: string | null;
  location_key: string | null;
  substrate_batch_key: string | null;
  planned_start_date: string | null;
  started_at: string | null;
  completed_at: string | null;
  source_plant_key: string | null;
  notes: string | null;
  phase_summary?: PhaseSummary | null;
  // REQ-013 §2 — set when the run was generated by a succession plan.
  succession_plan_key?: string | null;
  succession_sequence?: number | null;
  succession_total?: number | null;
  clone_from_run_key?: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PlantingRunCreate {
  name: string;
  run_type: PlantingRunType;
  location_key?: string | null;
  substrate_batch_key?: string | null;
  planned_start_date?: string | null;
  source_plant_key?: string | null;
  notes?: string | null;
  entries?: PlantingRunEntryCreate[];
}

export interface PlantingRunUpdate {
  name?: string;
  location_key?: string | null;
  notes?: string | null;
  planned_start_date?: string | null;
}

// ── REQ-013 §2 Succession plans (Staffelanbau) ────────────────────────

export interface SuccessionPlan {
  key: string;
  name: string;
  species_key: string;
  cultivar_key: string | null;
  interval_days: number;
  start_date: string;
  end_date: string;
  plants_per_batch: number;
  total_batches: number;
  completed_batches: number;
  status: SuccessionPlanStatus;
  reminder_days_before: number;
  location_key: string | null;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface SuccessionPlanCreate {
  name: string;
  species_key: string;
  cultivar_key?: string | null;
  interval_days: number;
  start_date: string;
  end_date: string;
  plants_per_batch: number;
  reminder_days_before?: number;
  location_key?: string | null;
  notes?: string | null;
}

export interface SuccessionPlanUpdate {
  name?: string;
  cultivar_key?: string | null;
  interval_days?: number;
  start_date?: string;
  end_date?: string;
  plants_per_batch?: number;
  reminder_days_before?: number;
  location_key?: string | null;
  notes?: string | null;
  status?: SuccessionPlanStatus;
}

export interface GenerateRunSummary {
  run_key: string;
  name: string;
  succession_sequence: number | null;
  succession_total: number | null;
  planned_start_date: string | null;
}

export interface GenerateRunsResponse {
  plan: SuccessionPlan;
  generated_count: number;
  runs: GenerateRunSummary[];
}

export interface GenerateNextRunResponse {
  plan: SuccessionPlan;
  generated: boolean;
  run: GenerateRunSummary | null;
}

export interface BatchCreatePlantsResponse {
  run_key: string;
  created_count: number;
  plant_keys: string[];
  instance_ids: string[];
  slots_assigned: number;
}

export interface AdoptPlantsRequest {
  plant_keys: string[];
}

export interface AdoptPlantsResponse {
  run_key: string;
  adopted_count: number;
  adopted_keys: string[];
  skipped: Array<{ key: string; reason: string }>;
  run_status: string;
  run_phase: string | null;
}

/**
 * The run-level phase transition (#1334).
 *
 * Named for what the server serves. The previous pair described a *batch* over
 * plants — counts, per-plant key lists, an `exclude_keys` filter — and no such
 * operation exists: REQ-013 v2.0 moved the phase onto the PlantingRun, so a run
 * has one phase and there is nothing to count, skip or exclude. Those fields
 * were a survivor of the pre-v2.0 model and read `undefined` at runtime.
 */
export interface RunTransitionRequest {
  target_phase_key: string;
  target_phase_name?: string;
  override_reason?: string;
}

export interface RunTransitionResponse {
  run_key: string;
  previous_phase: string | null;
  new_phase: string;
  new_phase_name: string;
  transitioned_at: string;
}

export interface BatchRemoveRequest {
  reason?: string;
  target_status?: 'completed' | 'cancelled';
}

export interface BatchRemoveResponse {
  run_key: string;
  removed_count: number;
  removed_keys: string[];
  final_status: string;
}

export interface PlantInRun {
  key: string;
  instance_id: string;
  species_key: string;
  cultivar_key: string | null;
  plant_name: string | null;
  planted_on: string;
  removed_on: string | null;
  current_phase: string;
  species: PlantSpeciesSummary | null;
  cultivar: PlantCultivarSummary | null;
  detached_at: string | null;
  detach_reason: string | null;
}

// Tank enums (REQ-014)

export type TankType = 'nutrient' | 'irrigation' | 'reservoir' | 'recirculation' | 'stock_solution';
export type FillType = 'full_change' | 'top_up' | 'adjustment';
export type TankMaterial = 'plastic' | 'stainless_steel' | 'glass' | 'ibc';
export type MaintenanceType =
  | 'water_change'
  | 'cleaning'
  | 'sanitization'
  | 'calibration'
  | 'filter_change'
  | 'pump_inspection';
export type MaintenancePriority = 'low' | 'medium' | 'high' | 'critical';
export type MaintenanceStatus = 'ok' | 'due_soon' | 'overdue';

// Tanks (REQ-014)

export interface Tank {
  key: string;
  name: string;
  tank_type: TankType;
  volume_liters: number;
  material: TankMaterial;
  has_lid: boolean;
  has_air_pump: boolean;
  has_circulation_pump: boolean;
  has_heater: boolean;
  is_light_proof: boolean;
  has_uv_sterilizer: boolean;
  has_ozone_generator: boolean;
  installed_on: string | null;
  location_key: string | null;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface TankCreate {
  name: string;
  tank_type: TankType;
  volume_liters: number;
  material?: TankMaterial;
  has_lid?: boolean;
  has_air_pump?: boolean;
  has_circulation_pump?: boolean;
  has_heater?: boolean;
  is_light_proof?: boolean;
  has_uv_sterilizer?: boolean;
  has_ozone_generator?: boolean;
  installed_on?: string | null;
  location_key?: string | null;
  notes?: string | null;
}

export interface TankUpdate {
  name?: string;
  tank_type?: TankType;
  volume_liters?: number;
  material?: TankMaterial;
  has_lid?: boolean;
  has_air_pump?: boolean;
  has_circulation_pump?: boolean;
  has_heater?: boolean;
  is_light_proof?: boolean;
  has_uv_sterilizer?: boolean;
  has_ozone_generator?: boolean;
  installed_on?: string | null;
  location_key?: string | null;
  notes?: string | null;
}

export interface TankState {
  key: string;
  tank_key: string;
  recorded_at: string | null;
  fill_level_liters: number | null;
  fill_level_percent: number | null;
  ph: number | null;
  ec_ms: number | null;
  water_temp_celsius: number | null;
  tds_ppm: number | null;
  dissolved_oxygen_mgl: number | null;
  orp_mv: number | null;
  source: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface TankStateCreate {
  fill_level_liters?: number | null;
  fill_level_percent?: number | null;
  ph?: number | null;
  ec_ms?: number | null;
  water_temp_celsius?: number | null;
  tds_ppm?: number | null;
  dissolved_oxygen_mgl?: number | null;
  orp_mv?: number | null;
  source?: string;
}

export interface MaintenanceLog {
  key: string;
  tank_key: string;
  maintenance_type: MaintenanceType;
  performed_at: string | null;
  performed_by: string;
  duration_minutes: number | null;
  products_used: string[];
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface MaintenanceLogCreate {
  maintenance_type: MaintenanceType;
  performed_by?: string;
  duration_minutes?: number | null;
  products_used?: string[];
  notes?: string | null;
}

export interface MaintenanceSchedule {
  key: string;
  tank_key: string;
  maintenance_type: MaintenanceType;
  interval_days: number;
  reminder_days_before: number;
  is_active: boolean;
  priority: MaintenancePriority;
  auto_create_task: boolean;
  instructions: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface MaintenanceScheduleCreate {
  maintenance_type: MaintenanceType;
  interval_days: number;
  reminder_days_before?: number;
  is_active?: boolean;
  priority?: MaintenancePriority;
  auto_create_task?: boolean;
  instructions?: string | null;
}

export interface MaintenanceScheduleUpdate {
  interval_days?: number;
  reminder_days_before?: number;
  is_active?: boolean;
  priority?: MaintenancePriority;
  auto_create_task?: boolean;
  instructions?: string | null;
}

export interface TankAlert {
  type: string;
  severity: string;
  message: string;
  value: number;
  limit?: number;
  limit_min?: number;
  limit_max?: number;
  factors?: string[];
  temp?: number;
}

// ── TankFillEvent types ──────────────────────────────────────────────

export interface FertilizerSnapshotData {
  product_key?: string | null;
  product_name: string;
  ml_per_liter: number;
}

export interface TankFillEvent {
  key: string;
  tank_key: string;
  filled_at: string | null;
  fill_type: FillType;
  volume_liters: number;
  mixing_result_key: string | null;
  nutrient_plan_key: string | null;
  target_ec_ms: number | null;
  target_ph: number | null;
  measured_ec_ms: number | null;
  measured_ph: number | null;
  water_source: string | null;
  water_mix_ratio_ro_percent: number | null;
  source_tank_key: string | null;
  fertilizers_used: FertilizerSnapshotData[];
  base_water_ec_ms: number | null;
  chlorine_ppm: number | null;
  chloramine_ppm: number | null;
  alkalinity_ppm: number | null;
  is_organic_fertilizers: boolean;
  performed_by: string | null;
  notes: string | null;
  water_defaults_source: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface TankFillEventCreate {
  fill_type: FillType;
  volume_liters: number;
  mixing_result_key?: string | null;
  nutrient_plan_key?: string | null;
  target_ec_ms?: number | null;
  target_ph?: number | null;
  measured_ec_ms?: number | null;
  measured_ph?: number | null;
  water_source?: string | null;
  water_mix_ratio_ro_percent?: number | null;
  source_tank_key?: string | null;
  fertilizers_used?: FertilizerSnapshotData[];
  base_water_ec_ms?: number | null;
  chlorine_ppm?: number | null;
  chloramine_ppm?: number | null;
  alkalinity_ppm?: number | null;
  is_organic_fertilizers?: boolean;
  performed_by?: string | null;
  notes?: string | null;
}

export interface TankFillEventStats {
  fill_type_counts: Record<string, number>;
  total_volume_liters: number;
  total_count: number;
  avg_ec_deviation_ms: number | null;
}

export interface FillEventResult {
  fill_event: TankFillEvent;
  tank_state: TankState | null;
  warnings: string[];
  water_defaults_source: string | null;
}

export interface DueMaintenance {
  tank_key: string;
  tank_name: string | null;
  schedule_key: string | null;
  maintenance_type: MaintenanceType;
  next_due: string;
  days_until: number;
  status: MaintenanceStatus;
  priority: MaintenancePriority;
}

// ── REQ-005 Sensor types ────────────────────────────────────────────

export interface Sensor {
  key: string;
  name: string;
  metric_type: string;
  ha_entity_id: string | null;
  unit_of_measurement: string | null;
  mqtt_topic: string | null;
  tank_key: string | null;
  site_key: string | null;
  location_key: string | null;
  is_active: boolean;
}

export interface SensorCreate {
  name: string;
  metric_type: string;
  ha_entity_id?: string | null;
  unit_of_measurement?: string | null;
  mqtt_topic?: string | null;
  tank_key?: string | null;
}

/**
 * Editable fields of a sensor.
 *
 * `is_active` is deliberately absent, although `Sensor` carries it: every read
 * filters `is_active == true` and there is no get-by-key or `include_inactive`
 * route, so writing `false` would make the sensor vanish from the only surfaces
 * that list it, with no way back through the API (#1339 review). Mirrors
 * `SensorUpdate` in `app/api/v1/tanks/schemas.py`.
 *
 * An explicit `null` clears a value; an omitted key leaves it untouched (the
 * routes dump with `exclude_unset`).
 */
export interface SensorUpdate {
  name?: string;
  metric_type?: string;
  ha_entity_id?: string | null;
  unit_of_measurement?: string | null;
  mqtt_topic?: string | null;
}

/**
 * One live reading, from one sensor.
 *
 * Keyed by sensor in `LiveStateResponse.readings`, because a reading belongs to
 * a sensor and not to a metric: two thermometers at opposite ends of one tent
 * are two readings, and neither may disappear.
 */
export interface LiveReadingEntry {
  /** Document key of the sensor. Null only for a sensor that was never persisted. */
  sensor_key: string | null;
  sensor_name: string | null;
  metric_type: string | null;
  value: number;
  last_changed: string | null;
  last_updated: string | null;
  /** When the entity last reported — the most reliable measurement instant. */
  last_reported: string | null;
  entity_id: string | null;
  unit: string | null;
}

/**
 * The one reading a metric is represented by in the derived single-value view.
 *
 * The freshest reading of the metric wins (ties break on the sensor key), and
 * the entry always says how many readings there were — a view that shows one
 * number must never pretend that one number was all there was.
 */
export interface LiveValueEntry extends LiveReadingEntry {
  /** How many sensors answered this metric. 1 means nothing was left out. */
  sensor_count: number;
  /** Keys of the readings this view does not show — look them up in `readings`. */
  superseded_sensor_keys: string[];
}

export interface LiveStateResponse {
  /** Every sensor that answered, keyed by its document key. The complete answer. */
  readings: Record<string, LiveReadingEntry>;
  /** Derived single-value view, keyed by metric type. Never more complete than `readings`. */
  values: Record<string, LiveValueEntry>;
  errors: Array<{ entity_id: string; error: string }>;
  source: string;
  message?: string | null;
}

// ── Observations / Sensor Readings (TimescaleDB) ───────────────────

export interface SensorReadingResponse {
  time: string;
  sensor_key: string;
  sensor_type: string;
  value: number;
  unit: string | null;
  source: string;
  quality_score: number | null;
  raw_value: number | null;
  metadata: Record<string, unknown> | null;
}

export interface AggregatedReadingResponse {
  bucket: string;
  sensor_key: string;
  sensor_type: string;
  avg_value: number;
  min_value: number;
  max_value: number;
  sample_count: number;
}

export type SensorReadingItem = SensorReadingResponse | AggregatedReadingResponse;

export interface ReadingsListResponse {
  items: SensorReadingItem[];
  total: number;
  resolution: string;
}

export interface TimeseriesStatusResponse {
  available: boolean;
}

// ── REQ-004 Fertilizer types ────────────────────────────────────────

export interface Fertilizer {
  key: string;
  origin?: DataOrigin;
  product_name: string;
  brand: string;
  fertilizer_type: FertilizerType;
  is_organic: boolean;
  tank_safe: boolean;
  recommended_application: ApplicationMethod;
  npk_ratio: [number, number, number];
  ec_contribution_per_ml: number;
  ec_contribution_uncertain: boolean;
  max_dose_ml_per_liter: number | null;
  mixing_priority: number;
  ph_effect: PhEffect;
  bioavailability: Bioavailability;
  shelf_life_days: number | null;
  storage_temp_min: number | null;
  storage_temp_max: number | null;
  // ── Area-based dosing fields (REQ-004 W-013, outdoor organic fertilization) ──
  application_rate_g_per_m2: number | null;
  application_rate_l_per_m2: number | null;
  dilution_ratio: string | null;
  nutrient_release_speed: NutrientReleaseSpeed | null;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface FertilizerCreate {
  product_name: string;
  brand?: string;
  fertilizer_type: FertilizerType;
  is_organic?: boolean;
  tank_safe?: boolean;
  recommended_application?: ApplicationMethod;
  npk_ratio?: [number, number, number];
  ec_contribution_per_ml?: number;
  ec_contribution_uncertain?: boolean;
  max_dose_ml_per_liter?: number | null;
  mixing_priority?: number;
  ph_effect?: PhEffect;
  bioavailability?: Bioavailability;
  shelf_life_days?: number | null;
  storage_temp_min?: number | null;
  storage_temp_max?: number | null;
  application_rate_g_per_m2?: number | null;
  application_rate_l_per_m2?: number | null;
  dilution_ratio?: string | null;
  nutrient_release_speed?: NutrientReleaseSpeed | null;
  notes?: string | null;
}

export interface FertilizerUpdate {
  product_name?: string;
  brand?: string;
  fertilizer_type?: FertilizerType;
  is_organic?: boolean;
  tank_safe?: boolean;
  recommended_application?: ApplicationMethod;
  npk_ratio?: [number, number, number];
  ec_contribution_per_ml?: number;
  ec_contribution_uncertain?: boolean;
  max_dose_ml_per_liter?: number | null;
  mixing_priority?: number;
  ph_effect?: PhEffect;
  bioavailability?: Bioavailability;
  shelf_life_days?: number | null;
  storage_temp_min?: number | null;
  storage_temp_max?: number | null;
  application_rate_g_per_m2?: number | null;
  application_rate_l_per_m2?: number | null;
  dilution_ratio?: string | null;
  nutrient_release_speed?: NutrientReleaseSpeed | null;
  notes?: string | null;
}

export interface FertilizerStock {
  key: string;
  fertilizer_key: string;
  current_volume_ml: number;
  purchase_date: string | null;
  expiry_date: string | null;
  batch_number: string;
  cost_per_liter: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface FertilizerStockCreate {
  current_volume_ml: number;
  purchase_date?: string | null;
  expiry_date?: string | null;
  batch_number?: string;
  cost_per_liter?: number | null;
}

export interface Incompatibility {
  fertilizer_key: string;
  product_name: string | null;
  reason: string;
  severity: IncompatibilitySeverity;
}

export interface FertilizerChannelUsage {
  channel_id: string;
  label: string;
  application_method: string;
  ml_per_liter: number;
}

export interface FertilizerPhaseUsage {
  phase_name: string;
  week_start: number;
  week_end: number;
  channels: FertilizerChannelUsage[];
}

export interface NutrientPlanUsage {
  key: string;
  name: string;
  phase_entries: FertilizerPhaseUsage[];
}

// ── REQ-004 Nutrient Plan types ─────────────────────────────────────

export interface NutrientPlan {
  key: string;
  origin?: DataOrigin;
  name: string;
  description: string;
  recommended_substrate_type: SubstrateType | null;
  reference_substrate_type: SubstrateType;
  author: string;
  is_template: boolean;
  version: string;
  tags: string[];
  cloned_from_key: string | null;
  watering_schedule: WateringSchedule | null;
  water_mix_ratio_ro_percent: number | null;
  cycle_restart_from_sequence: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface NutrientPlanCreate {
  name: string;
  description?: string;
  recommended_substrate_type?: SubstrateType | null;
  reference_substrate_type?: SubstrateType;
  author?: string;
  is_template?: boolean;
  version?: string;
  tags?: string[];
  watering_schedule?: WateringSchedule | null;
  water_mix_ratio_ro_percent?: number | null;
  cycle_restart_from_sequence?: number | null;
}

export interface NutrientPlanUpdate {
  name?: string;
  description?: string;
  recommended_substrate_type?: SubstrateType | null;
  reference_substrate_type?: SubstrateType;
  author?: string;
  is_template?: boolean;
  version?: string;
  tags?: string[];
  watering_schedule?: WateringSchedule | null;
  water_mix_ratio_ro_percent?: number | null;
  cycle_restart_from_sequence?: number | null;
}

export interface FertilizerDosage {
  fertilizer_key: string;
  ml_per_liter: number;
  optional: boolean;
  mixing_order: number;
}

// ── REQ-004 Multi-Channel Delivery types ──────────────────────────────

export interface FertigationParams {
  method: 'fertigation';
  runs_per_day: number;
  duration_seconds: number;
  flow_rate_ml_min: number | null;
}

export interface DrenchParams {
  method: 'drench';
  volume_per_feeding_liters: number;
}

export interface FoliarParams {
  method: 'foliar';
  volume_per_spray_liters: number;
}

export interface TopDressParams {
  method: 'top_dress';
  grams_per_plant: number | null;
  grams_per_m2: number | null;
}

export type MethodParams = FertigationParams | DrenchParams | FoliarParams | TopDressParams;

export interface DeliveryChannel {
  channel_id: string;
  label: string;
  application_method: ApplicationMethod;
  enabled: boolean;
  notes: string | null;
  schedule: WateringSchedule | null;
  target_ec_ms: number | null;
  target_ph: number | null;
  fertilizer_dosages: FertilizerDosage[];
  method_params: MethodParams | null;
}

export interface DeliveryChannelCreate {
  channel_id: string;
  label?: string;
  application_method: ApplicationMethod;
  enabled?: boolean;
  notes?: string | null;
  schedule?: WateringSchedule | null;
  target_ec_ms?: number | null;
  target_ph?: number | null;
  fertilizer_dosages?: FertilizerDosage[];
  method_params?: MethodParams | null;
}

export interface ChannelValidation {
  channel_id: string;
  label: string;
  issues: string[];
  ec_budget: { target: number; calculated: number; delta: number; tolerance: number } | null;
}

export interface NutrientPlanPhaseEntry {
  key: string;
  plan_key: string;
  phase_name: PhaseName;
  sequence_order: number;
  week_start: number;
  week_end: number;
  is_recurring: boolean;
  npk_ratio: [number, number, number];
  calcium_ppm: number | null;
  magnesium_ppm: number | null;
  target_ec_ms: number | null;
  reference_ec_ms: number | null;
  target_calcium_ppm: number | null;
  target_magnesium_ppm: number | null;
  reference_base_ec: number;
  notes: string | null;
  delivery_channels: DeliveryChannel[];
  watering_schedule_override: WateringSchedule | null;
  water_mix_ratio_ro_percent: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PhaseEntryCreate {
  phase_name: PhaseName;
  sequence_order: number;
  week_start: number;
  week_end: number;
  is_recurring?: boolean;
  npk_ratio?: [number, number, number];
  calcium_ppm?: number | null;
  magnesium_ppm?: number | null;
  target_ec_ms?: number | null;
  reference_ec_ms?: number | null;
  target_calcium_ppm?: number | null;
  target_magnesium_ppm?: number | null;
  reference_base_ec?: number;
  notes?: string | null;
  delivery_channels?: DeliveryChannelCreate[];
  watering_schedule_override?: WateringSchedule | null;
  water_mix_ratio_ro_percent?: number | null;
}

export interface PhaseEntryUpdate {
  phase_name?: PhaseName;
  sequence_order?: number;
  week_start?: number;
  week_end?: number;
  is_recurring?: boolean;
  npk_ratio?: [number, number, number];
  calcium_ppm?: number | null;
  magnesium_ppm?: number | null;
  target_ec_ms?: number | null;
  reference_ec_ms?: number | null;
  target_calcium_ppm?: number | null;
  target_magnesium_ppm?: number | null;
  reference_base_ec?: number;
  notes?: string | null;
  delivery_channels?: DeliveryChannelCreate[];
  watering_schedule_override?: WateringSchedule | null;
  water_mix_ratio_ro_percent?: number | null;
}

// ── REQ-004 Feeding Event types ─────────────────────────────────────

// @deprecated — use WateringLogFertilizer
export interface FeedingEventFertilizer {
  fertilizer_key: string;
  ml_applied: number;
}

// @deprecated — use WateringLog
export interface FeedingEvent {
  key: string;
  plant_key: string;
  timestamp: string | null;
  application_method: ApplicationMethod;
  is_supplemental: boolean;
  tank_fill_event_key: string | null;
  volume_applied_liters: number;
  fertilizers_used: FeedingEventFertilizer[];
  measured_ec_before: number | null;
  measured_ec_after: number | null;
  measured_ph_before: number | null;
  measured_ph_after: number | null;
  runoff_ec: number | null;
  runoff_ph: number | null;
  runoff_volume_liters: number | null;
  channel_id: string | null;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

// @deprecated — use WateringLogCreate
export interface FeedingEventCreate {
  plant_key: string;
  application_method?: ApplicationMethod;
  is_supplemental?: boolean;
  volume_applied_liters: number;
  fertilizers_used?: FeedingEventFertilizer[];
  measured_ec_before?: number | null;
  measured_ec_after?: number | null;
  measured_ph_before?: number | null;
  measured_ph_after?: number | null;
  runoff_ec?: number | null;
  runoff_ph?: number | null;
  runoff_volume_liters?: number | null;
  notes?: string | null;
}

// @deprecated — use WateringLogUpdate
export interface FeedingEventUpdate {
  application_method?: ApplicationMethod;
  is_supplemental?: boolean;
  volume_applied_liters?: number;
  measured_ec_before?: number | null;
  measured_ec_after?: number | null;
  measured_ph_before?: number | null;
  measured_ph_after?: number | null;
  runoff_ec?: number | null;
  runoff_ph?: number | null;
  runoff_volume_liters?: number | null;
  notes?: string | null;
}

// ── WateringLog types (unified, replaces WateringEvent + FeedingEvent) ──

export type WaterSource = 'tank' | 'tap' | 'osmose' | 'rainwater' | 'distilled' | 'well' | 'mixed';

export interface WateringLogFertilizer {
  fertilizer_key: string;
  ml_per_liter: number;
}

export interface ResolvedPlant {
  key: string;
  name: string;
}

export interface ResolvedFertilizer {
  key: string;
  name: string;
  ml_per_liter: number;
}

export interface WateringLog {
  key: string;
  logged_at: string | null;
  application_method: ApplicationMethod;
  is_supplemental: boolean;
  volume_liters: number;
  plant_keys: string[];
  slot_keys: string[];
  tank_fill_event_key: string | null;
  nutrient_plan_key: string | null;
  task_key: string | null;
  channel_id: string | null;
  fertilizers_used: WateringLogFertilizer[];
  ec_before: number | null;
  ec_after: number | null;
  ph_before: number | null;
  ph_after: number | null;
  runoff_ec: number | null;
  runoff_ph: number | null;
  runoff_volume_liters: number | null;
  water_source: WaterSource | null;
  performed_by: string | null;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
  resolved_plants: ResolvedPlant[];
  resolved_fertilizers: ResolvedFertilizer[];
}

export interface WateringLogCreate {
  application_method?: ApplicationMethod;
  is_supplemental?: boolean;
  volume_liters: number;
  plant_keys?: string[];
  slot_keys?: string[];
  tank_fill_event_key?: string | null;
  nutrient_plan_key?: string | null;
  channel_id?: string | null;
  fertilizers_used?: WateringLogFertilizer[];
  ec_before?: number | null;
  ec_after?: number | null;
  ph_before?: number | null;
  ph_after?: number | null;
  runoff_ec?: number | null;
  runoff_ph?: number | null;
  runoff_volume_liters?: number | null;
  water_source?: WaterSource | null;
  performed_by?: string | null;
  notes?: string | null;
}

export interface WateringLogUpdate {
  application_method?: ApplicationMethod;
  is_supplemental?: boolean;
  volume_liters?: number;
  ec_before?: number | null;
  ec_after?: number | null;
  ph_before?: number | null;
  ph_after?: number | null;
  runoff_ec?: number | null;
  runoff_ph?: number | null;
  runoff_volume_liters?: number | null;
  water_source?: WaterSource | null;
  performed_by?: string | null;
  notes?: string | null;
}

// ── WateringEvent types (deprecated) ────────────────────────────────
// @deprecated — use WateringLog

// @deprecated — use WateringLogFertilizer
export interface FertilizerSnapshot {
  product_key: string | null;
  product_name: string;
  ml_per_liter: number;
}

// @deprecated — use WateringLog
export interface WateringEvent {
  key: string;
  watered_at: string | null;
  application_method: ApplicationMethod;
  is_supplemental: boolean;
  volume_liters: number;
  plant_keys: string[];
  tank_fill_event_key: string | null;
  nutrient_plan_key: string | null;
  fertilizers_used: FertilizerSnapshot[];
  target_ec: number | null;
  target_ph: number | null;
  measured_ec: number | null;
  measured_ph: number | null;
  runoff_ec: number | null;
  runoff_ph: number | null;
  water_source: WaterSource | null;
  performed_by: string | null;
  channel_id: string | null;
  notes: string | null;
  created_at: string | null;
}

// @deprecated — use WateringLogCreate
export interface WateringEventCreate {
  application_method?: ApplicationMethod;
  is_supplemental?: boolean;
  volume_liters: number;
  plant_keys: string[];
  tank_fill_event_key?: string | null;
  nutrient_plan_key?: string | null;
  fertilizers_used?: FertilizerSnapshot[];
  target_ec?: number | null;
  target_ph?: number | null;
  measured_ec?: number | null;
  measured_ph?: number | null;
  runoff_ec?: number | null;
  runoff_ph?: number | null;
  water_source?: WaterSource | null;
  performed_by?: string | null;
  notes?: string | null;
}

export interface WateringEventWithWarnings {
  event: WateringEvent;
  warnings: Array<{ type: string; message: string }>;
}

export interface WateringMethodStats {
  method: string;
  count: number;
  total_volume: number;
}

export interface WateringStats {
  total_events: number;
  total_volume: number;
  by_method: WateringMethodStats[];
}

// ── REQ-004 Calculation types ───────────────────────────────────────

export interface MixingProtocolRequest {
  target_volume_liters: number;
  target_ec_ms: number;
  target_ph: number;
  base_water_ec: number;
  base_water_ph: number;
  fertilizer_keys: string[];
  substrate_type?: SubstrateType;
  // ── Additive REQ-004-A fields (AP-10) ──
  alkalinity_ppm?: number;
  phase?: PhaseName;
  recipe_ml_per_liter?: Record<string, number> | null;
}

export interface MixingDosage {
  fertilizer_key: string;
  product_name: string;
  ml_per_liter: number;
  total_ml: number;
  ec_contribution: number;
}

export interface MixingProtocolResponse {
  dosages: MixingDosage[];
  calculated_ec: number;
  ph_adjustment: { needed: boolean; direction: string; delta: number };
  warnings: string[];
  instructions: string[];
  // ── Additive REQ-004-A transparency fields (AP-10) ──
  ec_net: number;
  ec_ph_reserve: number;
  valid: boolean;
}

// ── Area-based dosing (REQ-004 W-013, AP-11) ────────────────────────

export interface AreaDosingRequest {
  fertilizer_keys: string[];
  area_m2?: number | null;
  location_key?: string | null;
  demand_level?: NutrientDemandLevel | null;
}

export interface AreaDosingItem {
  fertilizer_key: string | null;
  product_name: string;
  rate_g_per_m2: number | null;
  rate_l_per_m2: number | null;
  total_grams: number | null;
  total_liters: number | null;
  dilution_ratio: string | null;
  nutrient_release_speed: NutrientReleaseSpeed | null;
  note: string | null;
}

export interface AreaDosingResponse {
  area_m2: number;
  items: AreaDosingItem[];
  warnings: string[];
  instructions: string[];
}

export interface FlushingRequest {
  current_ec_ms: number;
  days_until_harvest: number;
  substrate_type?: SubstrateType;
}

export interface FlushingScheduleDay {
  day: number;
  absolute_day: number;
  target_ec_ms: number;
  action: string;
  dosage_percent: number;
}

export interface FlushingResponse {
  substrate_type: string;
  recommended_flush_days: number;
  flush_start_day: number;
  current_ec_ms: number;
  schedule: FlushingScheduleDay[];
}

export interface RunoffRequest {
  input_ec_ms: number;
  runoff_ec_ms: number;
  input_ph: number;
  runoff_ph: number;
  input_volume_liters: number;
  runoff_volume_liters: number;
}

export interface RunoffResponse {
  ec_delta: number;
  ec_status: string;
  ec_message: string;
  ph_delta: number;
  ph_status: string;
  ph_message: string;
  runoff_percent: number;
  volume_status: string;
  volume_message: string;
  overall_health: string;
}

export interface MixingSafetyRequest {
  fertilizer_keys: string[];
}

export interface MixingSafetyResponse {
  safe: boolean;
  warnings: string[];
}

// ── REQ-004-A Water mix reverse + EC budget ─────────────────────────

export interface WaterMixReverseRequest {
  tap_profile: {
    ec_ms: number;
    ph: number;
    alkalinity_ppm?: number;
    gh_ppm?: number;
    calcium_ppm?: number;
    magnesium_ppm?: number;
    chlorine_ppm?: number;
    chloramine_ppm?: number;
  };
  ro_profile?: { ec_ms?: number; ph?: number };
  target_base_ec_ms: number;
}

export interface WaterMixReverseResponse {
  ro_percent: number;
  effective_profile: {
    ec_ms: number;
    ph: number;
    alkalinity_ppm: number;
    calcium_ppm: number;
    magnesium_ppm: number;
    chlorine_ppm: number;
    chloramine_ppm: number;
  };
}

export interface EcBudgetFertilizerRequest {
  key: string;
  recipe_ml_per_liter?: number;
}

export interface EcBudgetRequest {
  base_water_ec: number;
  alkalinity_ppm?: number;
  target_ec: number;
  substrate: SubstrateType;
  phase: PhaseName;
  volume_liters: number;
  fertilizer_keys: EcBudgetFertilizerRequest[];
  calmag_key?: string;
  calmag_dose_ml_per_liter?: number;
  silicate_key?: string;
  silicate_dose_ml_per_liter?: number;
  substrate_cycles_used?: number;
  measured_ec?: number;
  measured_temp_celsius?: number;
}

export interface EcSegment {
  label: string;
  ec_contribution: number;
  color_hint: string;
  ml_per_liter: number;
  total_ml: number;
  warning: string | null;
}

export interface EcBudgetResponse {
  ec_mix: number;
  ec_net: number;
  ec_silicate: number;
  ec_calmag: number;
  ec_fertilizers: number;
  ec_ph_reserve: number;
  ec_final: number;
  ec_max: number;
  ec_target: number;
  ec_at_25_corrected: number | null;
  tolerance: number;
  valid: boolean;
  living_soil_bypass: boolean;
  segments: EcSegment[];
  warnings: string[];
  dosage_table: Array<{
    key: string;
    product_name: string;
    ml_per_liter: number;
    total_ml: number;
    ec_contribution: number;
  }>;
  dosage_instructions: string[];
}

export interface PlanValidationResult {
  completeness: { complete: boolean; issues: string[] };
  channel_validations: Array<{
    entry_key: string;
    phase_name: string;
    valid: boolean;
    channel_results: ChannelValidation[];
  }>;
  valid: boolean;
}

// ── REQ-010 IPM types ─────────────────────────────────────────────────

export type PestType = 'insect' | 'mite' | 'nematode' | 'mollusk';
export type PathogenType = 'fungal' | 'bacterial' | 'viral' | 'physiological';
export type TreatmentType = 'cultural' | 'biological' | 'chemical' | 'mechanical';
export type IpmApplicationMethod = 'spray' | 'drench' | 'granular' | 'release' | 'cultural';
export type DetectionDifficulty = 'easy' | 'medium' | 'hard';
export type PressureLevel = 'none' | 'low' | 'medium' | 'high' | 'critical';
export type PestSeverity = 'low' | 'medium' | 'high';
export type PlantPart = 'leaf' | 'stem' | 'root' | 'flower' | 'fruit';

export interface Pest {
  key: string;
  scientific_name: string;
  common_name: string;
  common_name_de: string | null;
  pest_type: string;
  lifecycle_days: number | null;
  optimal_temp_min: number | null;
  optimal_temp_max: number | null;
  detection_difficulty: string;
  description: string | null;
  description_de: string | null;
  damage_symptoms: string | null;
  damage_symptoms_de: string | null;
  affected_plant_parts: PlantPart[];
  host_plants: string[];
  host_plants_de: string[];
  prevention_tips: string | null;
  prevention_tips_de: string | null;
  monitoring_hints: string | null;
  monitoring_hints_de: string | null;
  severity: PestSeverity | null;
  optimal_humidity_min: number | null;
  optimal_humidity_max: number | null;
  detection_slug: string | null;
  reference_image_refs: string[];
  /**
   * REQ-044 — whether the pest's recognition class has usable few-shot
   * reference images indexed. Always `false` while pest detection is disabled.
   */
  has_reference_images: boolean;
  /** REQ-044 — number of active indexed reference prototypes (0 when none). */
  reference_image_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface PestCreate {
  scientific_name: string;
  common_name: string;
  pest_type?: string;
  lifecycle_days?: number | null;
  optimal_temp_min?: number | null;
  optimal_temp_max?: number | null;
  detection_difficulty?: string;
  description?: string | null;
  damage_symptoms?: string | null;
  affected_plant_parts?: PlantPart[];
  host_plants?: string[];
  prevention_tips?: string | null;
  monitoring_hints?: string | null;
  severity?: PestSeverity | null;
  optimal_humidity_min?: number | null;
  optimal_humidity_max?: number | null;
  detection_slug?: string | null;
  reference_image_refs?: string[];
}

export interface PestUpdate {
  scientific_name?: string;
  common_name?: string;
  pest_type?: string;
  lifecycle_days?: number | null;
  optimal_temp_min?: number | null;
  optimal_temp_max?: number | null;
  detection_difficulty?: string;
  description?: string | null;
  damage_symptoms?: string | null;
  affected_plant_parts?: PlantPart[];
  host_plants?: string[];
  prevention_tips?: string | null;
  monitoring_hints?: string | null;
  severity?: PestSeverity | null;
  optimal_humidity_min?: number | null;
  optimal_humidity_max?: number | null;
  detection_slug?: string | null;
  reference_image_refs?: string[];
}

export interface Beneficial {
  key: string;
  slug: string;
  common_name: string;
  scientific_name: string;
  description: string | null;
  preys_on: string[];
}

export interface PestDetail {
  pest: Pest;
  treatments: Treatment[];
  beneficials: Beneficial[];
  detection_symptom_hint: string | null;
}

export type PestImageStatus = 'private' | 'promoted';

/**
 * Provenance of a pest detail gallery tile:
 * - `contribution` — a curated, deletable/promotable user upload;
 * - `inspection`   — a read-only photo of one of the tenant's own inspections
 *   in which this pest was detected (no delete/promote);
 * - `recognition`  — a read-only, GLOBAL reference image of the pest's few-shot
 *   recognition index (REQ-044). The `uri` is the external, CC-licensed
 *   `source_url` (no local pixel); render it via a native `<img>` and show the
 *   `attribution` / `license` next to it (CC-BY obligation).
 */
export type PestImageSource = 'contribution' | 'inspection' | 'recognition';

export interface PestImage {
  id: string;
  pest_key: string;
  attachment_id: string;
  uri: string;
  thumbnail_uri: string | null;
  // null for inspection- and recognition-sourced photos (no contribution lifecycle).
  status: PestImageStatus | null;
  caption: string | null;
  // SEC-002 — only set for the caller's own contributions. For foreign promoted
  // images the backend returns null (a contributor's identity is PII).
  contributed_by: string | null;
  created_at: string | null;
  is_own: boolean;
  // REQ-010 curation state. Always true for tiles in the default gallery; only
  // the platform-admin "show deselected" view ever returns false tiles (dimmed
  // with a "deselected" badge). Defaults to true for back-compat with older
  // payloads that predate the field.
  is_active?: boolean;
  // Defaults to 'contribution' for back-compat with older payloads.
  source?: PestImageSource;
  // Only set for `source === 'recognition'` — the CC-BY attribution / license of
  // the externally-hosted image, surfaced as a caption (null otherwise).
  attribution?: string | null;
  license?: string | null;
}

export interface Disease {
  key: string;
  origin?: DataOrigin;
  scientific_name: string;
  common_name: string;
  pathogen_type: string;
  incubation_period_days: number | null;
  environmental_triggers: string[];
  affected_plant_parts: string[];
  description: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface DiseaseCreate {
  scientific_name: string;
  common_name: string;
  pathogen_type: string;
  incubation_period_days?: number | null;
  environmental_triggers?: string[];
  affected_plant_parts?: string[];
  description?: string | null;
}

export interface DiseaseUpdate {
  scientific_name?: string;
  common_name?: string;
  pathogen_type?: string;
  incubation_period_days?: number | null;
  environmental_triggers?: string[];
  affected_plant_parts?: string[];
  description?: string | null;
}

export interface Treatment {
  key: string;
  origin?: DataOrigin;
  name: string;
  name_de: string | null;
  treatment_type: string;
  active_ingredient: string | null;
  application_method: string;
  safety_interval_days: number;
  dosage_per_liter: number | null;
  protective_equipment: string[];
  description: string | null;
  description_de: string | null;
  how_to_apply: string | null;
  how_to_apply_de: string | null;
  mode_of_action: string | null;
  mode_of_action_de: string | null;
  precautions: string | null;
  precautions_de: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface TreatmentCreate {
  name: string;
  name_de?: string | null;
  treatment_type: string;
  active_ingredient?: string | null;
  application_method?: string;
  safety_interval_days?: number;
  dosage_per_liter?: number | null;
  protective_equipment?: string[];
  description?: string | null;
  description_de?: string | null;
  how_to_apply?: string | null;
  how_to_apply_de?: string | null;
  mode_of_action?: string | null;
  mode_of_action_de?: string | null;
  precautions?: string | null;
  precautions_de?: string | null;
}

export interface TreatmentUpdate {
  name?: string;
  name_de?: string | null;
  treatment_type?: string;
  active_ingredient?: string | null;
  application_method?: string;
  safety_interval_days?: number;
  dosage_per_liter?: number | null;
  protective_equipment?: string[];
  description?: string | null;
  description_de?: string | null;
  how_to_apply?: string | null;
  how_to_apply_de?: string | null;
  mode_of_action?: string | null;
  mode_of_action_de?: string | null;
  precautions?: string | null;
  precautions_de?: string | null;
}

export interface TreatmentTargetRef {
  key: string;
  common_name: string;
  common_name_de: string | null;
  scientific_name: string;
}

export interface TreatmentDetail {
  treatment: Treatment;
  targeted_pests: TreatmentTargetRef[];
  targeted_diseases: TreatmentTargetRef[];
}

export interface Inspection {
  key: string;
  plant_key: string;
  inspector: string;
  inspected_at: string | null;
  pressure_level: string;
  detected_pest_keys: string[];
  detected_disease_keys: string[];
  symptoms_observed: string[];
  environmental_conditions: Record<string, number> | null;
  photo_refs: string[];
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface InspectionCreate {
  inspector?: string;
  pressure_level?: string;
  detected_pest_keys?: string[];
  detected_disease_keys?: string[];
  symptoms_observed?: string[];
  environmental_conditions?: Record<string, number> | null;
  photo_refs?: string[];
  notes?: string | null;
}

export interface TreatmentApplication {
  key: string;
  treatment_key: string;
  plant_key: string;
  applied_at: string | null;
  dosage: number | null;
  water_volume_liters: number | null;
  efficacy_rating: string | null;
  applied_by: string;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface TreatmentApplicationCreate {
  treatment_key: string;
  dosage?: number | null;
  water_volume_liters?: number | null;
  efficacy_rating?: string | null;
  applied_by?: string;
  notes?: string | null;
}

export interface KarenzPeriod {
  active_ingredient: string | null;
  treatment_name: string | null;
  applied_at: string | null;
  safety_interval_days: number | null;
  safe_date: string | null;
}

export interface HarvestSafety {
  can_harvest: boolean;
  blocking_treatments: Array<Record<string, unknown>>;
}

// ── REQ-007 Harvest enums ─────────────────────────────────────────────

export type HarvestType = 'partial' | 'final' | 'continuous';
export type QualityGrade = 'a_plus' | 'a' | 'b' | 'c' | 'd';
export type HarvestIndicatorType =
  'trichome' | 'color' | 'brix' | 'size' | 'days_since_flowering' | 'aroma' | 'texture' | 'foliage';
export type RipenessStage = 'immature' | 'approaching' | 'peak' | 'overripe';

// ── REQ-007 Harvest types ─────────────────────────────────────────────

export interface HarvestIndicator {
  key: string;
  indicator_type: HarvestIndicatorType;
  measurement_unit: string;
  measurement_method: string;
  observation_frequency: string;
  reliability_score: number;
  species_key: string | null;
  description: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface HarvestIndicatorCreate {
  indicator_type: HarvestIndicatorType;
  measurement_unit?: string;
  measurement_method?: string;
  observation_frequency?: string;
  reliability_score?: number;
  species_key?: string | null;
  description?: string | null;
}

export interface HarvestObservation {
  key: string;
  plant_key: string;
  observed_at: string | null;
  observer: string;
  indicator_key: string;
  measurements: Record<string, unknown>;
  ripeness_assessment: RipenessStage;
  days_to_harvest_estimate: number | null;
  photo_refs: string[];
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface HarvestObservationCreate {
  indicator_key?: string;
  observer?: string;
  measurements?: Record<string, unknown>;
  ripeness_assessment?: RipenessStage;
  days_to_harvest_estimate?: number | null;
  photo_refs?: string[];
  notes?: string | null;
}

export interface HarvestBatch {
  key: string;
  batch_id: string | null;
  plant_key: string;
  harvest_date: string | null;
  harvest_type: HarvestType;
  wet_weight_g: number | null;
  estimated_dry_weight_g: number | null;
  actual_dry_weight_g: number | null;
  quality_grade: QualityGrade | null;
  harvester: string;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface HarvestBatchCreate {
  batch_id?: string;
  harvest_type?: HarvestType;
  harvest_date?: string;
  wet_weight_g?: number | null;
  estimated_dry_weight_g?: number | null;
  harvester?: string;
  notes?: string | null;
}

export interface HarvestBatchUpdate {
  harvest_type?: HarvestType;
  wet_weight_g?: number | null;
  estimated_dry_weight_g?: number | null;
  actual_dry_weight_g?: number | null;
  quality_grade?: QualityGrade | null;
  harvester?: string;
  notes?: string | null;
}

export interface QualityAssessment {
  key: string;
  batch_key: string;
  assessed_at: string | null;
  assessed_by: string;
  appearance_score: number;
  aroma_score: number;
  color_score: number;
  defects: string[];
  overall_score: number;
  grade: QualityGrade | null;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface QualityAssessmentCreate {
  assessed_by?: string;
  appearance_score?: number;
  aroma_score?: number;
  color_score?: number;
  defects?: string[];
  notes?: string | null;
}

export interface YieldMetric {
  key: string;
  batch_key: string;
  yield_per_plant_g: number;
  yield_per_m2_g: number;
  total_yield_g: number;
  trim_waste_percent: number;
  usable_yield_g: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface YieldMetricCreate {
  yield_per_plant_g?: number;
  yield_per_m2_g?: number;
  total_yield_g?: number;
  trim_waste_percent?: number;
  usable_yield_g?: number;
}

export interface ReadinessIndicatorBreakdown {
  indicator_key: string;
  stage: string;
  score: number;
  reliability: number;
  weighted_contribution: number;
}

export interface ReadinessAssessment {
  overall_score: number;
  recommendation: string;
  estimated_days: number | null;
  indicators: ReadinessIndicatorBreakdown[];
}

export interface YieldStats {
  species_key: string;
  total_batches: number;
  avg_yield_per_plant_g: number;
  avg_yield_per_m2_g: number;
  total_yield_g: number;
  avg_trim_waste_percent: number;
}

// ── REQ-008 Post-Harvest types ────────────────────────────────────────

export type PostHarvestStage = 'drying' | 'curing' | 'stored' | 'released';

export type DryingMethod = 'hang_dry' | 'rack_dry' | 'dehydrator' | 'air_cure';

export type PostHarvestSpeciesType = 'flower' | 'herb' | 'root' | 'fruit' | 'mushroom';

export type MoldAlertSeverity = 'warning' | 'critical';

export type StorageVisualCondition =
  'excellent' | 'good' | 'acceptable' | 'concerning' | 'critical';

export type StorageAromaQuality = 'excellent' | 'good' | 'acceptable' | 'off' | 'moldy';

export type PesticideResidueStatus = 'untested' | 'clean' | 'within_limits' | 'residue_detected';

export interface PostHarvestBatch {
  key: string;
  harvest_batch_key: string;
  plant_key: string;
  stage: PostHarvestStage;
  species_type: PostHarvestSpeciesType;
  drying_method: DryingMethod;
  start_weight_g: number | null;
  current_weight_g: number | null;
  target_moisture_percent: number;
  dryness_progress_percent: number;
  ready_for_curing: boolean;
  snap_test_passed: boolean | null;
  water_activity: number | null;
  storage_location: string | null;
  pesticide_residue_status: PesticideResidueStatus;
  started_at: string | null;
  drying_started_at: string | null;
  curing_started_at: string | null;
  stored_at: string | null;
  released_at: string | null;
  completed_at: string | null;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface StartDryingRequest {
  harvest_batch_key: string;
  species_type?: PostHarvestSpeciesType;
  drying_method?: DryingMethod;
  start_weight_g?: number | null;
  target_moisture_percent?: number;
  notes?: string | null;
}

export interface DryingProgress {
  key: string;
  batch_key: string;
  start_weight_g: number;
  current_weight_g: number;
  target_weight_g: number;
  weight_loss_percent: number;
  dryness_progress_percent: number;
  snap_test_ready: boolean;
  snap_test_passed: boolean | null;
  over_dried: boolean;
  estimated_days_remaining: number;
  next_action: string;
  water_activity: number | null;
  co2_ppm_current: number | null;
  recorded_at: string | null;
  notes: string | null;
}

export interface DryingProgressCreate {
  current_weight_g: number;
  water_activity?: number | null;
  co2_ppm?: number | null;
  snap_test_passed?: boolean | null;
  notes?: string | null;
}

export interface StorageObservation {
  key: string;
  batch_key: string;
  weight_g: number | null;
  temperature_c: number | null;
  rh_percent: number | null;
  water_activity: number | null;
  co2_ppm: number | null;
  visual_condition: StorageVisualCondition;
  aroma_quality: StorageAromaQuality;
  defects_observed: string[];
  observer: string;
  notes: string | null;
  observed_at: string | null;
}

export interface StorageObservationCreate {
  weight_g?: number | null;
  temperature_c?: number | null;
  rh_percent?: number | null;
  water_activity?: number | null;
  co2_ppm?: number | null;
  visual_condition?: StorageVisualCondition;
  aroma_quality?: StorageAromaQuality;
  defects_observed?: string[];
  observer?: string;
  notes?: string | null;
}

export interface MoldAlert {
  key: string;
  batch_key: string;
  severity: MoldAlertSeverity;
  trigger_reason: string;
  affected_location: string;
  action_taken: string | null;
  triggered_at: string | null;
  resolved_at: string | null;
}

export interface PostHarvestBatchDetail {
  batch: PostHarvestBatch;
  latest_drying_progress: DryingProgress | null;
  open_mold_alerts: number;
}

// ── REQ-006 Task & Workflow types ─────────────────────────────────────

export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'skipped' | 'cancelled';
export type TaskPriority = 'low' | 'medium' | 'high' | 'critical';
export type TaskCategory =
  | 'maintenance'
  | 'watering'
  | 'feeding'
  | 'training'
  | 'pest_control'
  | 'harvest'
  | 'pruning'
  | 'transplant'
  | 'monitoring'
  | 'cleaning'
  | 'care_reminder';
export type TriggerType = 'manual' | 'time_based' | 'event_based' | 'conditional';
export type SkillLevel = 'beginner' | 'intermediate' | 'advanced' | 'expert';
export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced' | 'expert';
export type WorkflowTargetType = 'plant_instance' | 'planting_run' | 'location' | 'tank';

export interface WorkflowTemplate {
  key: string;
  name: string;
  description: string | null;
  created_by: string;
  version: string;
  species_compatible: string[];
  growth_system: string | null;
  difficulty_level: string;
  category: string;
  tags: string[];
  is_system: boolean;
  auto_generated: boolean;
  species_key: string | null;
  species_name: string;
  total_duration_days: number;
  assigned_entity_count: number;
  target_entity_types: WorkflowTargetType[];
  phase_sequence_key: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface WorkflowTemplateCreate {
  name: string;
  description?: string | null;
  created_by?: string;
  version?: string;
  species_compatible?: string[];
  species_key?: string | null;
  growth_system?: string | null;
  difficulty_level?: string;
  category?: string;
  tags?: string[];
  is_system?: boolean;
  target_entity_types?: WorkflowTargetType[];
}

export interface WorkflowTemplateUpdate {
  name?: string;
  description?: string | null;
  version?: string;
  species_compatible?: string[];
  growth_system?: string | null;
  difficulty_level?: string;
  category?: string;
  tags?: string[];
  target_entity_types?: WorkflowTargetType[];
}

export interface ChecklistItem {
  text: string;
  done: boolean;
  order: number;
}

// Phase Definitions & Sequences

export interface PhaseDefinition {
  key: string;
  name: string;
  display_name: string;
  display_name_de: string;
  description: string;
  description_de: string;
  typical_duration_days: number;
  stress_tolerance: string;
  watering_interval_days: number | null;
  illustration: string;
  tags: string[];
  is_system: boolean;
  usage_count: number;
  created_at: string | null;
  updated_at: string | null;
}

/**
 * A species that traverses a phase definition, with the phase's typical duration
 * (FIX-01 List 2, from GET /phase-definitions/{key}/species).
 */
export interface PhaseDefinitionSpecies {
  key: string;
  scientific_name: string;
  common_names: string[];
  typical_duration_days: number;
  illustration: string;
}

/**
 * A tenant's active plant instance currently in a given phase definition
 * (FIX-01 List 1, from GET /t/{slug}/plant-instances/by-phase-definition/{key}).
 * ``days_in_phase`` is derived on the client from ``current_phase_started_at``.
 */
export interface PlantInstanceInPhase {
  key: string;
  instance_id: string;
  plant_name: string | null;
  species_key: string;
  species_scientific_name: string | null;
  species_common_names: string[];
  location_key: string | null;
  location_name: string | null;
  slot_key: string | null;
  slot_label: string | null;
  current_phase_key: string | null;
  current_phase_started_at: string | null;
}

/** List-1 payload: the tenant's active instances in a phase definition + total count (R3). */
export interface PlantInstancesInPhase {
  total: number;
  items: PlantInstanceInPhase[];
}

export interface PhaseDefinitionCreate {
  name: string;
  display_name?: string;
  display_name_de?: string;
  description?: string;
  description_de?: string;
  typical_duration_days: number;
  stress_tolerance?: string;
  watering_interval_days?: number | null;
  tags?: string[];
}

export interface PhaseDefinitionUpdate {
  name?: string;
  display_name?: string;
  display_name_de?: string;
  description?: string;
  description_de?: string;
  typical_duration_days?: number;
  stress_tolerance?: string;
  watering_interval_days?: number | null;
  tags?: string[];
}

export interface PhaseSequenceEntry {
  key: string;
  phase_sequence_key: string;
  phase_definition_key: string;
  sequence_order: number;
  override_duration_days: number | null;
  effective_duration_days: number;
  is_terminal: boolean;
  allows_harvest: boolean;
  is_recurring: boolean;
  phase_definition: PhaseDefinition | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PhaseSequenceEntryCreate {
  phase_definition_key: string;
  sequence_order?: number;
  override_duration_days?: number | null;
  is_terminal?: boolean;
  allows_harvest?: boolean;
  is_recurring?: boolean;
}

export interface PhaseSequenceEntryUpdate {
  phase_definition_key?: string;
  sequence_order?: number;
  override_duration_days?: number | null;
  is_terminal?: boolean;
  allows_harvest?: boolean;
  is_recurring?: boolean;
}

export interface PhaseSequence {
  key: string;
  name: string;
  display_name: string;
  display_name_de: string;
  description: string;
  description_de: string;
  species_key: string;
  cycle_type: CycleType;
  is_repeating: boolean;
  cycle_restart_entry_order: number | null;
  typical_lifespan_years: number | null;
  dormancy_required: boolean;
  vernalization_required: boolean;
  vernalization_min_days: number | null;
  photoperiod_type: PhotoperiodType;
  critical_day_length_hours: number | null;
  is_system: boolean;
  tags: string[];
  entries: PhaseSequenceEntry[];
  created_at: string | null;
  updated_at: string | null;
}

export interface PhaseSequenceCreate {
  name: string;
  display_name?: string;
  display_name_de?: string;
  description?: string;
  description_de?: string;
  cycle_type?: string;
  is_repeating?: boolean;
  cycle_restart_entry_order?: number | null;
  tags?: string[];
}

export interface PhaseSequenceUpdate {
  name?: string;
  display_name?: string;
  display_name_de?: string;
  description?: string;
  description_de?: string;
  cycle_type?: string;
  is_repeating?: boolean;
  cycle_restart_entry_order?: number | null;
  tags?: string[];
}

export interface WorkflowPhase {
  key: string;
  workflow_template_key: string;
  name: string;
  description: string;
  phase_order: number;
  duration_days: number;
  stress_tolerance: string;
  trigger_phase: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface WorkflowPhaseCreate {
  name: string;
  description?: string;
  phase_order?: number;
  duration_days?: number;
  stress_tolerance?: string;
  trigger_phase?: string | null;
}

export interface WorkflowPhaseUpdate {
  name?: string;
  description?: string;
  phase_order?: number;
  duration_days?: number;
  stress_tolerance?: string;
  trigger_phase?: string | null;
}

export interface WorkflowPhaseSuggestion {
  name: string;
  duration_days: number;
  stress_tolerance: string;
  trigger_phase: string | null;
  used_by_species: string[];
  usage_count: number;
}

export interface TaskTemplate {
  key: string;
  name: string;
  name_de: string;
  instruction: string;
  instruction_de: string;
  description: string;
  description_de: string;
  rationale: string;
  rationale_de: string;
  category: string;
  trigger_type: string;
  trigger_phase: string | null;
  phase_display_name: string;
  phase_duration_days: number;
  phase_stress_tolerance: string;
  days_offset: number;
  stress_level: string;
  estimated_duration_minutes: number | null;
  requires_photo: boolean;
  timer_duration_seconds: number | null;
  timer_label: string | null;
  tools_required: string[];
  skill_level: string;
  optimal_time_of_day: string | null;
  workflow_template_key: string | null;
  workflow_phase_key: string | null;
  phase_definition_key: string | null;
  activity_key: string | null;
  sequence_order: number;
  recovery_days: number;
  is_optional: boolean;
  enabled: boolean;
  default_checklist: ChecklistItem[];
  require_all_checklist_items: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface TaskTemplateCreate {
  name: string;
  instruction?: string;
  category?: string;
  trigger_type?: string;
  trigger_phase?: string | null;
  days_offset?: number;
  stress_level?: string;
  estimated_duration_minutes?: number | null;
  requires_photo?: boolean;
  timer_duration_seconds?: number | null;
  timer_label?: string | null;
  tools_required?: string[];
  skill_level?: string;
  optimal_time_of_day?: string | null;
  workflow_template_key?: string | null;
  workflow_phase_key?: string | null;
  sequence_order?: number;
  default_checklist?: ChecklistItem[];
  require_all_checklist_items?: boolean;
}

export interface TaskTemplateUpdate {
  name?: string;
  instruction?: string;
  category?: string;
  trigger_type?: string;
  trigger_phase?: string | null;
  days_offset?: number;
  stress_level?: string;
  estimated_duration_minutes?: number | null;
  requires_photo?: boolean;
  timer_duration_seconds?: number | null;
  timer_label?: string | null;
  tools_required?: string[];
  skill_level?: string;
  optimal_time_of_day?: string | null;
  workflow_phase_key?: string | null;
  sequence_order?: number;
  default_checklist?: ChecklistItem[];
  require_all_checklist_items?: boolean;
}

/** REQ-006 FreeStyle task origin (#1082). Orthogonal to `TaskCategory`. */
export type TaskOrigin = 'user' | 'system' | 'pipeline';

export interface TaskItem {
  key: string;
  name: string;
  name_de: string;
  instruction: string;
  instruction_de: string;
  category: string;
  /** REQ-006 FreeStyle provenance (#1082) — who produced the task, orthogonal to
   *  `category`. `'user'` for interactive tasks; `'system'`/`'pipeline'` mark a
   *  machine producer. Drives the machine-generated badge and filter. */
  origin: TaskOrigin;
  /** Free-form producer id, e.g. `'goose/leaf-analysis'` (empty for user tasks). */
  source: string;
  /** Optional producer run reference, shown on the task detail page. */
  source_run_ref: string | null;
  /** Optional producer dedupe key (idempotent machine creation). */
  external_ref: string | null;
  entity_key: string | null;
  entity_type: string | null;
  due_date: string | null;
  scheduled_time: string | null;
  status: string;
  priority: string;
  skill_level: string;
  stress_level: string;
  estimated_duration_minutes: number | null;
  actual_duration_minutes: number | null;
  requires_photo: boolean;
  photo_refs: string[];
  timer_duration_seconds: number | null;
  timer_label: string | null;
  completion_notes: string | null;
  difficulty_rating: number | null;
  quality_rating: number | null;
  tags: string[];
  checklist: ChecklistItem[];
  assigned_to_user_key: string | null;
  recurrence_rule: string | null;
  recurrence_end_date: string | null;
  parent_recurring_task_key: string | null;
  trigger_phase: string | null;
  trigger_phase_override: string | null;
  reopened_at: string | null;
  reopened_from_status: string | null;
  started_at: string | null;
  completed_at: string | null;
  activity_key: string | null;
  template_key: string | null;
  workflow_execution_key: string | null;
  watering_event_key: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface TaskItemCreate {
  name: string;
  name_de?: string;
  instruction?: string;
  instruction_de?: string;
  category?: string;
  entity_key?: string | null;
  entity_type?: string | null;
  due_date?: string | null;
  scheduled_time?: string | null;
  priority?: string;
  skill_level?: string;
  stress_level?: string;
  estimated_duration_minutes?: number | null;
  requires_photo?: boolean;
  timer_duration_seconds?: number | null;
  timer_label?: string | null;
  tags?: string[];
  checklist?: ChecklistItem[];
  assigned_to_user_key?: string | null;
  recurrence_rule?: string | null;
  recurrence_end_date?: string | null;
  trigger_phase?: string | null;
}

export interface TaskItemUpdate {
  name?: string;
  instruction?: string;
  category?: string;
  due_date?: string | null;
  scheduled_time?: string | null;
  priority?: string;
  skill_level?: string;
  stress_level?: string;
  estimated_duration_minutes?: number | null;
  requires_photo?: boolean;
  timer_duration_seconds?: number | null;
  timer_label?: string | null;
  tags?: string[];
  checklist?: ChecklistItem[];
  assigned_to_user_key?: string | null;
  recurrence_rule?: string | null;
  recurrence_end_date?: string | null;
  trigger_phase_override?: string | null;
}

/** Thumbnail renditions of a task photo, or `null` while they generate. */
export interface TaskPhotoThumbnailUris {
  small: string;
  medium: string;
  large: string;
}

/**
 * One uploaded task photo (REQ-006), addressed by its NFR-013 attachment.
 *
 * Replaces the `{ url, filename, size_bytes }` shape the client used to declare:
 * that described an unauthenticated static file under `/uploads/tasks`, which
 * no endpoint ever wrote and which #1339 removed. `uri` is permission-gated, so
 * it must be fetched through the authenticated client (`AuthImage`) rather than
 * handed to an `<img src>`.
 */
export interface TaskPhoto {
  attachment_id: string;
  /** Stable, tenant-scoped download URI for the original object. */
  uri: string;
  thumbnail_uris: TaskPhotoThumbnailUris | null;
  mime_type: string;
  byte_size: number;
  original_filename: string;
}

export interface TaskCompleteRequest {
  completion_notes?: string | null;
  actual_duration_minutes?: number | null;
  photo_refs?: string[];
  difficulty_rating?: number | null;
  quality_rating?: number | null;
}

export interface TaskCloneRequest {
  target_entity_key?: string | null;
  target_entity_type?: string | null;
  due_date_offset_days?: number | null;
}

export interface TaskComment {
  key: string;
  task_key: string;
  comment_text: string;
  created_by: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface TaskAuditEntry {
  key: string;
  task_key: string;
  changed_at: string | null;
  changed_by: string;
  action: string;
  field: string | null;
  old_value: string | null;
  new_value: string | null;
}

export interface BatchResponse {
  succeeded: string[];
  failed: { key: string; error: string }[];
}

export interface WorkflowAddTaskRequest {
  name: string;
  instruction?: string;
  category?: string;
  due_date?: string | null;
  priority?: string;
  trigger_phase?: string | null;
  estimated_duration_minutes?: number | null;
  tags?: string[];
  checklist?: ChecklistItem[];
}

export interface WorkflowExecution {
  key: string;
  workflow_template_key: string;
  entity_key: string;
  entity_type: string;
  started_at: string | null;
  completed_at: string | null;
  completion_percentage: number;
  on_schedule: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface WorkflowInstantiateRequest {
  entity_key: string;
  entity_type: WorkflowTargetType;
}

export interface HSTValidationResult {
  can_perform: boolean;
  reason: string;
  recovery_status: string;
}

// ── REQ-023 Auth types ──────────────────────────────────────────────

export type AuthProviderType = 'local' | 'google' | 'github' | 'apple' | 'oidc';
/**
 * REQ-049 axis 1 — the ranked domain role, exactly one per membership.
 * `lead` replaced `admin`: the old value conflated "may delete domain records"
 * with "administers the tenant", and the latter moved to `AdminScope`.
 */
export type TenantRole = 'viewer' | 'grower' | 'lead';

/**
 * REQ-049 axis 2 — administrative scopes, granted in addition to the domain
 * role and independent of its rank. A viewer may hold `management`.
 */
export type AdminScope = 'management' | 'technical';
export type TenantType = 'personal' | 'organization';
export type InvitationStatus = 'pending' | 'accepted' | 'expired' | 'revoked';
export type InvitationType = 'email' | 'link';

export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserProfile {
  key: string;
  email: string;
  display_name: string;
  email_verified: boolean;
  is_active: boolean;
  avatar_url: string | null;
  locale: string;
  timezone: string;
  last_login_at: string | null;
  created_at: string | null;
  /** Global platform-admin flag — gates admin-only UI (e.g. reference-image curation). */
  is_platform_admin: boolean;
}

export interface UserProfileUpdate {
  display_name?: string;
  avatar_url?: string | null;
  locale?: string;
  timezone?: string;
}

export interface AuthProviderInfo {
  key: string;
  provider: AuthProviderType;
  provider_email: string | null;
  provider_display_name: string | null;
  linked_at: string | null;
  last_used_at: string | null;
}

export interface SessionInfo {
  key: string;
  user_agent: string | null;
  /**
   * Self-chosen label of a device paired via QR code (#1118), capped at 64
   * characters by the backend. `null` for browser and OAuth sessions — and for
   * sessions stored before the field existed — in which case the session list
   * falls back to `user_agent`.
   */
  device_name: string | null;
  ip_address: string | null;
  created_at: string | null;
  expires_at: string;
  is_current: boolean;
  is_persistent: boolean;
}

export interface OAuthProviderListItem {
  slug: string;
  display_name: string;
  icon_url: string | null;
}

export interface ApiKeyCreate {
  label: string;
  tenant_scope?: string | null;
}

export interface ApiKeyCreated {
  key: string;
  label: string;
  raw_key: string;
  key_prefix: string;
  tenant_scope: string | null;
  created_at: string | null;
}

export interface ApiKeySummary {
  key: string;
  label: string;
  key_prefix: string;
  tenant_scope: string | null;
  revoked: boolean;
  last_used_at: string | null;
  created_at: string | null;
}

/**
 * One freshly minted QR pairing code (#1118) — the response of
 * `POST /auth/device-pairing` (201).
 *
 * `payload_version`, `server_url` and `code` are exactly the three fields the
 * scanner reads, encoded as `{"v": …, "url": …, "code": …}`; nothing else from
 * this object belongs in the QR.
 *
 * The code is a one-time credential with a lifetime of well under two minutes.
 * It must never be persisted (Redux, `localStorage`, a URL) and never rendered
 * as readable text — a bystander who reads it off the screen can pair their own
 * device. It lives in the dialog's component state and dies with it.
 */
export interface DevicePairingCreated {
  /** Version of the QR payload contract; stamped into the payload as `v`. */
  payload_version: number;
  /**
   * Base URL the paired app must call. Comes from the server's configured
   * `app_base_url` (REQ-032 QR SSOT), *not* from `window.location`: the browser
   * generating the code and the phone scanning it are not necessarily on the
   * same network path.
   */
  server_url: string;
  code: string;
  expires_at: string;
  /**
   * Seconds left at the moment the response was produced — already relative, so
   * the countdown seeds from this directly. Recomputing it from `expires_at`
   * would make the display depend on the browser's clock being correct.
   */
  expires_in: number;
}

// ── REQ-024 Tenant types ────────────────────────────────────────────

export interface Tenant {
  key: string;
  name: string;
  slug: string;
  tenant_type: TenantType;
  description: string | null;
  avatar_url: string | null;
  owner_key: string;
  max_members: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface TenantWithRole extends Tenant {
  role: TenantRole;
  admin_scopes: AdminScope[];
}

export interface TenantCreate {
  name: string;
  description?: string | null;
  tenant_type?: TenantType;
}

export interface TenantUpdate {
  name?: string;
  description?: string | null;
  avatar_url?: string | null;
}

export interface Membership {
  key: string;
  user_key: string;
  tenant_key: string;
  role: TenantRole;
  admin_scopes: AdminScope[];
  display_name: string;
  email: string;
  joined_at: string | null;
}

export interface Invitation {
  key: string;
  tenant_key: string;
  email: string | null;
  role: TenantRole;
  invitation_type: InvitationType;
  status: InvitationStatus;
  created_by: string;
  expires_at: string;
  created_at: string | null;
}

export interface InvitationCreate {
  email: string;
  role: TenantRole;
}

export interface InvitationLinkCreate {
  role: TenantRole;
  max_uses?: number;
}

export interface LocationAssignment {
  key: string;
  membership_key: string;
  location_key: string;
  tenant_key: string;
  created_at: string | null;
}

// ── REQ-019 Substrate extensions ────────────────────────────────────

export type IrrigationStrategy = 'infrequent' | 'moderate' | 'frequent' | 'continuous';

// ── REQ-022 Care Reminders ──────────────────────────────────────────

export type CareStyleType =
  | 'tropical'
  | 'succulent'
  | 'orchid'
  | 'calathea'
  | 'herb_tropical'
  | 'mediterranean'
  | 'fern'
  | 'cactus'
  | 'custom';
export type ReminderType =
  | 'watering'
  | 'fertilizing'
  | 'repotting'
  | 'pest_check'
  | 'location_check'
  | 'humidity_check'
  // REQ-022 v2.5 outdoor + overwintering reminder types (§3.2)
  | 'deadheading'
  | 'tuber_dig'
  | 'storage_check'
  | 'spring_uncover'
  | 'winter_protection'
  // REQ-047 §2.5 season-/dormancy-driven control reminders
  | 'dormancy_health_check'
  | 'quarter_climate_check';
export type ConfirmAction = 'confirmed' | 'snoozed' | 'skipped';
export type WateringMethod = 'soak' | 'drench_and_drain' | 'top_water' | 'bottom_water';

export interface CareProfile {
  key: string;
  care_style: CareStyleType;
  watering_interval_days: number;
  winter_watering_multiplier: number;
  watering_method: WateringMethod;
  water_quality_hint: string | null;
  fertilizing_interval_days: number;
  fertilizing_active_months: number[];
  repotting_interval_months: number;
  pest_check_interval_days: number;
  location_check_enabled: boolean;
  location_check_months: number[];
  humidity_check_enabled: boolean;
  humidity_check_interval_days: number;
  adaptive_learning_enabled: boolean;
  auto_create_watering_task: boolean;
  auto_create_fertilizing_task: boolean;
  auto_create_repotting_task: boolean;
  auto_create_pest_check_task: boolean;
  watering_interval_learned: number | null;
  fertilizing_interval_learned: number | null;
  notes: string | null;
  auto_generated: boolean;
  plant_key: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface CareConfirmation {
  key: string;
  plant_key: string;
  care_profile_key: string;
  reminder_type: ReminderType;
  action: ConfirmAction;
  confirmed_at: string;
  snooze_days: number | null;
  watering_log_key: string | null;
  notes: string | null;
  interval_at_time: number | null;
}

export interface CareDashboardEntry {
  plant_key: string;
  plant_name: string;
  species_name: string | null;
  reminder_type: ReminderType;
  urgency: 'overdue' | 'due_today' | 'upcoming' | 'not_due';
  due_date: string | null;
  care_profile_key: string;
  task_key: string | null;
}

// ── REQ-020 Onboarding ──────────────────────────────────────────────

export type ExperienceLevel = 'beginner' | 'intermediate' | 'expert';
export type StarterKitDifficulty = 'beginner' | 'intermediate' | 'advanced';

// ── REQ-042 Module visibility ────────────────────────────────────────
export type ModuleVisibilityState = 'enabled' | 'disabled';

export interface StarterKit {
  key: string;
  kit_id: string;
  name_i18n: Record<string, string>;
  description_i18n: Record<string, string>;
  difficulty: StarterKitDifficulty;
  icon: string;
  plant_count_suggestion: number;
  site_type: SiteType;
  species_keys: string[];
  cultivar_keys: string[];
  toxicity_warning: boolean;
  workflow_template_keys: string[];
  includes_nutrient_plan: boolean;
  nutrient_plan_keys: string[];
  tags: string[];
  sort_order: number;
}

export interface SpeciesAvailability {
  species_key: string;
  available: boolean;
}

export interface StarterKitWithAvailability extends StarterKit {
  species_availability: SpeciesAvailability[];
}

export interface PlantConfig {
  species_key: string;
  count: number;
  initial_phase: PhaseName;
}

export interface OnboardingState {
  key: string;
  user_key: string;
  completed: boolean;
  skipped: boolean;
  completed_at: string | null;
  selected_kit_id: string | null;
  selected_experience_level: ExperienceLevel | null;
  wizard_step: number;
  created_entities: Record<string, string[]>;
  site_name: string;
  site_type: string | null;
  selected_site_key: string | null;
  plant_count: number | null;
  plant_configs: PlantConfig[];
  favorite_species_keys: string[];
  favorite_nutrient_plan_keys: string[];
}

// ── REQ-020 Favorites ───────────────────────────────────────────────

export interface FavoriteEntry {
  key: string;
  target_key: string;
  target_type: string;
  source: string;
  cascade_from_key: string | null;
  favorited_at: string;
}

export interface NutrientPlanFertilizerInfo {
  key: string;
  product_name: string;
  brand: string | null;
}

export interface NutrientPlanMatch {
  plan_key: string;
  name: string;
  description: string | null;
  substrate_type: string | null;
  fertilizer_count: number;
  fertilizers: NutrientPlanFertilizerInfo[];
}

// ── REQ-021 User Preferences ────────────────────────────────────────

export interface UserPreference {
  key: string;
  user_key: string;
  experience_level: ExperienceLevel;
  onboarding_completed: boolean;
  locale: string;
  theme: string;
  watering_can_liters: number;
  smart_home_enabled: boolean;
  /** UI-NFR-019 — touch-optimized kiosk shell active. */
  kiosk_enabled?: boolean;
  /** UI-NFR-019 — WCAG-AAA high-contrast theme (R-005 kiosk default, R-045 standalone). */
  high_contrast?: boolean;
  module_visibility?: Record<string, ModuleVisibilityState>;
  /** REQ-045 — personalized dashboard layout; null/absent = experience default. */
  dashboard_layout?: DashboardLayout | null;
}

// ── REQ-045 Individualisierbares Dashboard ───────────────────────────
export type DashboardBreakpoint = 'lg' | 'md' | 'sm';

export interface DashboardWidgetInstance {
  instance_id: string;
  widget_key: string;
  config?: Record<string, unknown>;
}

export interface WidgetPlacement {
  instance_id: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface DashboardLayout {
  schema_version: number;
  widgets: DashboardWidgetInstance[];
  placements: Partial<Record<DashboardBreakpoint, WidgetPlacement[]>>;
}

export interface DashboardWidgetCatalogEntry {
  widget_key: string;
  category: string;
  default_level: ExperienceLevel;
  default_size: { w: number; h: number };
  min_size: { w: number; h: number };
  max_size: { w: number; h: number };
  required_module: string | null;
  available: boolean;
  unavailable_reason: string | null;
}

export interface DashboardWidgetCatalogResponse {
  widgets: DashboardWidgetCatalogEntry[];
}

export interface DashboardAggregatedResponse {
  generated_at: string;
  tenant_key: string;
  widgets: Record<string, unknown>;
}

// ── Watering Schedule types ──────────────────────────────────────────

export type ScheduleMode = 'weekdays' | 'interval';

export interface WateringSchedule {
  schedule_mode: ScheduleMode;
  weekday_schedule: number[];
  interval_days: number | null;
  preferred_time: string | null;
  application_method: string;
  reminder_hours_before: number;
  times_per_day: number;
}

export interface ChannelCalendarEntry {
  channel_id: string;
  label: string;
  application_method: string;
  phase_name: string;
  dates: string[];
  times_per_day: number;
}

export interface WateringScheduleCalendarResponse {
  run_key: string;
  has_schedule: boolean;
  plan_key?: string;
  plan_name?: string;
  schedule?: WateringSchedule;
  dates: string[];
  channel_calendars?: ChannelCalendarEntry[];
  times_per_day?: number;
}

export interface NutrientPlanAssignRequest {
  plan_key: string;
  assigned_by?: string;
}

export interface NutrientPlanAssignResponse {
  run_key: string;
  plan_key: string;
  edge_key: string;
}

// ── REQ-015 Calendar Types ───────────────────────────────────────────

export type CalendarEventCategory =
  | 'training'
  | 'pruning'
  | 'transplanting'
  | 'feeding'
  | 'ipm'
  | 'harvest'
  | 'maintenance'
  | 'phase_transition'
  | 'tank_maintenance'
  | 'watering_forecast'
  | 'custom';
export type CalendarEventSource =
  'task' | 'phase_transition' | 'maintenance_log' | 'watering' | 'watering_forecast';

export interface CalendarEvent {
  id: string;
  title: string;
  description: string;
  category: CalendarEventCategory;
  source: CalendarEventSource;
  color: string;
  start: string | null;
  end: string | null;
  all_day: boolean;
  plant_key: string | null;
  task_key: string | null;
  site_key: string | null;
  location_key: string | null;
  metadata: Record<string, unknown>;
}

export interface CalendarEventsResponse {
  events: CalendarEvent[];
  total: number;
}

export interface CalendarFeedFilters {
  categories: string[];
  site_key: string | null;
}

export interface CalendarFeed {
  key: string;
  name: string;
  token: string;
  user_key: string;
  filters: CalendarFeedFilters;
  is_active: boolean;
  ical_url: string;
  created_at: string | null;
  updated_at: string | null;
}

// Sowing Calendar (REQ-015 §3.8)

export type SowingPhase =
  | 'indoor_sowing'
  | 'outdoor_planting'
  | 'growth'
  | 'harvest'
  | 'flowering'
  | 'germination'
  | 'seedling'
  | 'vegetative'
  | 'flushing'
  | 'ripening';

export interface SowingBar {
  phase: SowingPhase;
  color: string;
  start_date: string;
  end_date: string;
  label: string;
}

export interface SowingCalendarEntry {
  species_key: string;
  species_name: string;
  common_name: string;
  link_species_key: string;
  plant_category: string | null;
  bars: SowingBar[];
}

export interface FrostConfig {
  last_frost_date: string;
  first_frost_date: string | null;
  eisheilige_date: string;
}

export interface SowingCalendarResponse {
  entries: SowingCalendarEntry[];
  frost_config: FrostConfig;
  year: number;
  total: number;
}

// Season Overview (REQ-015 §3.9)

export interface MonthSummary {
  month: number;
  month_name: string;
  sowing_count: number;
  harvest_count: number;
  bloom_count: number;
  task_count: number;
  top_tasks: string[];
  is_current: boolean;
}

export interface SeasonOverviewResponse {
  site_key: string;
  site_name: string;
  year: number;
  months: MonthSummary[];
}

export interface WateringConfirmRequest {
  run_key: string;
  task_key: string;
  channel_id?: string;
  measured_ec?: number;
  measured_ph?: number;
  volume_liters?: number;
  overrides?: Record<string, unknown>;
}

export interface WateringQuickConfirmRequest {
  run_key: string;
  task_key: string;
  channel_id?: string;
}

export interface WateringConfirmResponse {
  watering_event_key: string;
  feeding_events_created: number;
  task_completed: boolean;
  warnings: Record<string, unknown>[];
}

// ── Watering Volume Suggestion ────────────────────────────────────────

export interface VolumeSuggestion {
  volume_ml: number;
  volume_ml_min: number;
  volume_ml_max: number;
  source: string;
  adjustments: string[];
  /** REQ-003 E7: phase is watered without nutrients (flush/rest regime). */
  water_only?: boolean;
  /** Human-readable phase-regime note from the resolver (e.g. flush/rest/standard). */
  regime_note?: string;
}

// ── REQ-012 Import Types ─────────────────────────────────────────────

export type EntityType = 'species' | 'cultivar' | 'botanical_family';
export type DuplicateStrategy = 'skip' | 'update' | 'fail';
export type ImportJobStatus =
  'uploaded' | 'validating' | 'preview_ready' | 'confirmed' | 'importing' | 'completed' | 'failed';
export type RowStatus = 'valid' | 'invalid' | 'duplicate';

export interface RowValidationError {
  field: string;
  message: string;
  value: string;
}

export interface PreviewRow {
  row_number: number;
  data: Record<string, string>;
  status: RowStatus;
  errors: RowValidationError[];
  duplicate_key: string | null;
}

export interface ImportResult {
  created: number;
  updated: number;
  skipped: number;
  failed: number;
  errors: string[];
}

export interface ImportJob {
  key: string;
  entity_type: EntityType;
  status: ImportJobStatus;
  filename: string;
  row_count: number;
  duplicate_strategy: DuplicateStrategy;
  preview_rows: PreviewRow[];
  result: ImportResult | null;
  error_message: string | null;
  created_at: string | null;
}

// Activities (Stammdaten)

export interface Activity {
  key: string;
  tenant_key: string;
  name: string;
  name_de: string;
  description: string;
  description_de: string;
  category: ActivityCategory;
  stress_level: StressLevel;
  skill_level: SkillLevel;
  recovery_days_default: number;
  recovery_days_by_species: Record<string, number>;
  forbidden_phases: string[];
  restricted_sub_phases: string[];
  tools_required: string[];
  estimated_duration_minutes: number | null;
  requires_photo: boolean;
  species_compatible: string[];
  is_system: boolean;
  sort_order: number;
  tags: string[];
  created_at: string | null;
  updated_at: string | null;
}

export interface ActivityCreate {
  name: string;
  name_de?: string;
  description?: string;
  description_de?: string;
  category?: ActivityCategory;
  stress_level?: StressLevel;
  skill_level?: SkillLevel;
  recovery_days_default?: number;
  recovery_days_by_species?: Record<string, number>;
  forbidden_phases?: string[];
  restricted_sub_phases?: string[];
  tools_required?: string[];
  estimated_duration_minutes?: number | null;
  requires_photo?: boolean;
  species_compatible?: string[];
  sort_order?: number;
  tags?: string[];
}

// ── Activity Plans ──

export interface TaskTemplateResponse {
  key: string;
  name: string;
  name_de: string;
  instruction: string;
  instruction_de: string;
  trigger_phase: string | null;
  phase_display_name: string;
  phase_duration_days: number;
  phase_stress_tolerance: string;
  days_offset: number;
  rationale: string;
  rationale_de: string;
  category: string;
  stress_level: string;
  skill_level: string;
  estimated_duration_minutes: number | null;
  tools_required: string[];
  recovery_days: number;
  is_optional: boolean;
  enabled: boolean;
  activity_key: string | null;
  description: string;
  description_de: string;
}

export interface ActivityPlanResponse {
  workflow_template_key: string;
  name: string;
  species_name: string;
  species_key: string | null;
  auto_generated: boolean;
  growth_system: string | null;
  skill_level_filter: string | null;
  total_activities: number;
  total_duration_days: number;
  /**
   * True while this plan is still the globally generated shared template every
   * tenant reads (#1003). The first edit materialises a private copy owned by
   * this tenant, after which it is false. Nothing else distinguishes the two.
   */
  is_shared_template: boolean;
  templates: TaskTemplateResponse[];
}

export interface ActivityPlanGenerateRequest {
  species_key: string;
  lifecycle_key?: string | null;
  growth_system?: string | null;
  skill_level?: string | null;
  force_regenerate?: boolean;
}

export interface ActivityPlanApplyRequest {
  workflow_template_key: string;
  plant_key?: string | null;
  run_key?: string | null;
}

export interface ActivityPlanApplyResponse {
  created_count: number;
  task_keys: string[];
  plant_count: number | null;
  total_tasks: number | null;
}

export interface TaskTemplateUpdateRequest {
  enabled?: boolean | null;
  days_offset?: number | null;
  trigger_phase?: string | null;
}

// ── Admin Platform Types ──────────────────────────────────────────────

export interface AdminTenant {
  key: string;
  name: string;
  slug: string;
  tenant_type: TenantType;
  description: string | null;
  owner_user_key: string;
  is_active: boolean;
  is_platform: boolean;
  max_members: number;
  member_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface AdminUserTenantRole {
  tenant_key: string;
  tenant_name: string;
  tenant_slug: string;
  role: TenantRole;
}

export interface AdminUser {
  key: string;
  email: string;
  display_name: string;
  is_active: boolean;
  email_verified: boolean;
  last_login_at: string | null;
  created_at: string | null;
  tenant_count: number;
  roles: AdminUserTenantRole[];
}

export interface AdminPlatformStats {
  total_users: number;
  active_users: number;
  total_tenants: number;
  active_tenants: number;
  total_memberships: number;
}

export interface AdminTenantUpdate {
  name?: string;
  description?: string;
  max_members?: number;
  is_active?: boolean;
}

export interface AdminUserUpdate {
  display_name?: string;
  is_active?: boolean;
  email_verified?: boolean;
}

export interface AdminTenantMember {
  membership_key: string;
  user_key: string;
  display_name: string;
  email: string;
  role: TenantRole;
  is_active: boolean;
  joined_at: string | null;
}

export interface AdminAddMemberRequest {
  user_key: string;
  role: TenantRole;
}

export interface AdminUserMembership {
  membership_key: string;
  tenant_key: string;
  tenant_name: string;
  tenant_slug: string;
  role: TenantRole;
  is_active: boolean;
  joined_at: string | null;
}

export interface AdminAddUserToTenantRequest {
  tenant_key: string;
  role: TenantRole;
}

// ── Notifications (REQ-030) ──────────────────────────────────────────

export type NotificationUrgency = 'low' | 'normal' | 'high' | 'critical';
export type NotificationStatusValue = 'pending' | 'delivered' | 'failed';

export interface NotificationAction {
  action_id: string;
  title: string;
  uri: string | null;
}

export interface NotificationResponse {
  key: string;
  tenant_key: string;
  user_key: string;
  notification_type: string;
  title: string;
  body: string;
  urgency: NotificationUrgency;
  data: Record<string, unknown>;
  actions: NotificationAction[];
  image_url: string | null;
  group_key: string | null;
  channels_sent: string[];
  channels_failed: string[];
  status: NotificationStatusValue;
  read_at: string | null;
  acted_at: string | null;
  escalation_level: number;
  parent_notification_key: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface NotificationListResponse {
  items: NotificationResponse[];
  total: number;
  unread_count: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface ChannelPreference {
  enabled: boolean;
  priority: number;
  config: Record<string, unknown>;
}

export interface QuietHoursPreference {
  enabled: boolean;
  start: string;
  end: string;
  timezone: string;
}

export interface BatchingPreference {
  enabled: boolean;
  window_minutes: number;
  max_batch_size: number;
}

export interface EscalationPreference {
  watering_enabled: boolean;
  escalation_days: number[];
}

export interface TypeOverride {
  channels: string[];
  ignore_quiet_hours: boolean;
}

export interface DailySummaryPreference {
  enabled: boolean;
  time: string;
  channel: string;
}

export interface NotificationPreferencesResponse {
  key: string | null;
  user_key: string;
  channels: Record<string, ChannelPreference>;
  quiet_hours: QuietHoursPreference;
  batching: BatchingPreference;
  escalation: EscalationPreference;
  type_overrides: Record<string, TypeOverride>;
  daily_summary: DailySummaryPreference;
  created_at: string | null;
  updated_at: string | null;
}

export interface NotificationPreferencesRequest {
  channels: Record<string, ChannelPreference>;
  quiet_hours: QuietHoursPreference;
  batching: BatchingPreference;
  escalation: EscalationPreference;
  type_overrides: Record<string, TypeOverride>;
  daily_summary: DailySummaryPreference;
}

export interface ChannelStatusResponse {
  channel_key: string;
  healthy: boolean;
  supports_actions: boolean;
  supports_batching: boolean;
}

export interface TestNotificationResponse {
  status: string;
  channel_key: string;
  success: boolean;
  error: string | null;
}

// Web Push (PWA notification channel)

export interface PwaVapidPublicKeyResponse {
  vapid_public_key: string;
}

export interface PwaSubscribeRequest {
  endpoint: string;
  p256dh: string;
  auth: string;
  user_agent: string;
}

export interface PwaSubscribeResponse {
  endpoint: string;
}

export interface PwaUnsubscribeRequest {
  endpoint: string;
}

// REQ-025 — Privacy / consent (Art. 7 DSGVO)

export interface ConsentRecord {
  purpose: string;
  label: string;
  description: string;
  legal_basis: string;
  required: boolean;
  granted: boolean;
  granted_at: string | null;
  revoked_at: string | null;
}

// REQ-029 / REQ-029-A — AI plant identification (Phase 1: Pl@ntNet-first)

/** Plant organ shown in the photo — improves identification accuracy. */
export type PlantOrgan = 'leaf' | 'flower' | 'fruit' | 'bark' | 'habit' | 'auto';

/** Per-adapter configuration/health state from GET /recognition/status. */
export interface IdentificationAdapterStatus {
  configured: boolean;
  supports_health: boolean;
  rate_limit_per_day: number | null;
}

/** Feature availability payload used to toggle the camera UI. */
export interface IdentificationStatus {
  available: boolean;
  primary_adapter: string;
  active_adapter: string | null;
  supports_health: boolean;
  adapters: Record<string, IdentificationAdapterStatus>;
}

// REQ-029-A — self-hosted DINOv2 recognition (admin status view)

/** Inference-service health/model info from GET /admin/recognition/status. */
export interface RecognitionInferenceService {
  enabled: boolean;
  url: string | null;
  ready: boolean;
  model: string | null;
  dim: number | null;
  license: string | null;
}

/** Reference-image coverage across the species catalogue. */
export interface RecognitionCoverage {
  total_species: number;
  /** Species already handled by an acquisition run (one job each) — grows during a run. */
  processed_species: number;
  usable_species: number;
}

/** Read-only recognition configuration sourced from server env/settings. */
export interface RecognitionConfig {
  primary_adapter: string;
  confidence_auto_accept: number;
  confidence_min_show: number;
  reference_image_min_usable: number;
  use_wikimedia: boolean;
}

/** Platform-admin status payload from GET /admin/recognition/status. */
export interface RecognitionStatus {
  feature_enabled: boolean;
  local_adapter_available: boolean;
  inference_service: RecognitionInferenceService;
  coverage: RecognitionCoverage;
  config: RecognitionConfig;
}

/** A single identification candidate returned by /identify. */
export interface IdentificationSuggestion {
  rank: number;
  scientific_name: string;
  common_names: string[];
  family: string | null;
  genus: string | null;
  confidence: number;
  external_id: string;
  image_url: string | null;
  gbif_id: number | null;
  matched_species_key: string | null;
  species_in_database: boolean;
  auto_accept: boolean;
}

/** Result of an /identify call. */
export interface IdentifyResult {
  request_key: string | null;
  is_plant: boolean;
  suggestions: IdentificationSuggestion[];
  message: string | null;
}

/** Result of a /{request_key}/select call — drives the "create plant" step. */
export interface IdentificationSelection {
  request_key: string;
  selected_rank: number;
  matched_species_key: string | null;
  scientific_name: string;
  common_names: string[];
  family: string | null;
  genus: string | null;
  gbif_id: number | null;
  confidence: number;
  species_in_database: boolean;
}

/** A single entry in the identification history. */
export interface IdentificationHistoryEntry {
  key: string | null;
  adapter_key: string;
  request_type: string;
  image_organ: string;
  status: string;
  results: IdentificationSuggestion[];
  selected_result_rank: number | null;
  /**
   * Key of the plant instance created from this identification result (#630).
   * `null` until the grower turned a suggestion into an actual plant; once set,
   * the history surfaces a link to the instance's detail page.
   */
  plant_instance_key: string | null;
  created_at: string | null;
}

/** Result of linking an identification request to a created plant instance (#630). */
export interface IdentificationInstanceLink {
  request_key: string;
  plant_instance_key: string;
}

// ── REQ-044 Bildbasierte Schädlingserkennung ──────────────────────────

export type PestFindingCategory = 'pest' | 'beneficial' | 'symptom' | 'unknown';
export type PestFindingMode = 'direct' | 'symptom';

export interface PestBoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface PestFinding {
  label: string;
  category: PestFindingCategory;
  common_name: string;
  confidence: number;
  mode: PestFindingMode;
  bounding_box: PestBoundingBox | null;
  matched_pest_key: string | null;
  matched_beneficial_key: string | null;
}

export interface PestDetectionResult {
  key: string | null;
  plant_instance_key: string | null;
  source: string;
  adapter_key: string;
  is_confident: boolean;
  trigger: string;
  findings: PestFinding[];
  tiles_processed: number;
  suggested_next_step: 'ipm_inspection' | 'none';
  image_hash: string;
  disclaimer: string;
  created_at: string | null;
}

export interface PestAdapterStatus {
  configured: boolean;
  is_external: boolean;
  requires_consent: string | null;
  supports_modes: string[];
}

export interface PestDetectionStatus {
  available: boolean;
  feature_enabled: boolean;
  primary_adapter: string;
  active_adapter: string | null;
  adapters: Record<string, PestAdapterStatus>;
}

export interface PestCreateInspectionResult {
  inspection_key: string | null;
  detected_pest_keys: string[];
}

// ── REQ-044 Pest few-shot index admin ─────────────────────────────────

export interface PestCoverageEntry {
  label: string;
  common_name: string;
  category: string;
  scientific_name: string;
  gbif_taxon_key: string | null;
  total: number;
  active: number;
  target: number;
  usable: boolean;
}

export interface PestRecognitionStatus {
  feature_enabled: boolean;
  service_ready: boolean;
  index_count: number;
  target_per_class: number;
  classes: PestCoverageEntry[];
}

export interface PestAcquireResponse {
  status: string;
  task_id: string | null;
}

export interface PestCurationImage {
  id: number;
  source_url: string;
  license: string | null;
  attribution: string | null;
  source: string | null;
  source_record_id: string | null;
  is_active: boolean;
  exclusion_reason: string | null;
}

export interface PestCurationImageList {
  label: string;
  count: number;
  active_count: number;
  images: PestCurationImage[];
}

// ── REQ-010 — user-contributed pest image moderation (global promotion) ──

/**
 * A single user-contributed pest image as seen by a platform admin for
 * cross-tenant moderation. `content_uri` / `thumbnail_uri` point at the global
 * content endpoint so the admin can preview the pixels regardless of which
 * tenant owns them. Mirrors the backend `PestContributionModerationItem`.
 */
export interface PestContribution {
  id: string;
  pest_key: string;
  attachment_id: string;
  content_uri: string;
  thumbnail_uri: string | null;
  status: PestImageStatus;
  caption: string | null;
  tenant_key: string;
  contributed_by: string;
  created_at: string | null;
  promoted_at: string | null;
  promoted_by: string | null;
}

export interface PestContributionList {
  pest_key: string;
  count: number;
  promoted_count: number;
  images: PestContribution[];
}

export interface PromotePestContributionResponse {
  id: string;
  pest_key: string;
  status: PestImageStatus;
  // REQ-010 curation state — false once a platform admin deselects the image.
  is_active: boolean;
  promoted_at: string | null;
  promoted_by: string | null;
}

// ── REQ-022 — Overwintering profiles & winter-hardiness traffic light ──

export type HardinessRating = 'hardy' | 'needs_protection' | 'frost_free' | 'dig_and_store';

export type WinterAction =
  'none' | 'mulch' | 'fleece' | 'earth_up' | 'move_indoors' | 'dig_store' | 'wrap';

export type SpringAction = 'uncover' | 'move_outdoors' | 'replant' | 'prune' | 'harden_off';

export type TuberStatus =
  'planted' | 'growing' | 'dig_pending' | 'drying' | 'stored' | 'pre_sprouting';

export type WinterQuarterLight = 'bright' | 'semi_bright' | 'dark';

export type WinterWatering = 'none' | 'minimal' | 'reduced' | 'normal';

/** REQ-022 winter-hardiness traffic light — dashboard aggregate colour. */
export type WinterHardinessLight = 'green' | 'yellow' | 'red';

/**
 * REQ-022 §OverwinteringProfile — overwintering configuration for a single
 * plant instance or planting run (mirrors the backend response schema).
 */
export interface OverwinteringProfile {
  key: string;
  plant_key: string | null;
  planting_run_key: string | null;
  hardiness_zone_min: string | null;
  hardiness_rating: HardinessRating;
  winter_action: WinterAction;
  winter_action_month: number;
  spring_action: SpringAction | null;
  spring_action_month: number | null;
  winter_quarter_key: string | null;
  winter_quarter_temp_min: number | null;
  winter_quarter_temp_max: number | null;
  winter_quarter_light: WinterQuarterLight | null;
  winter_watering: WinterWatering | null;
  storage_medium: string | null;
  storage_check_interval_days: number | null;
  tuber_status: TuberStatus | null;
  notes: string | null;
  auto_generated: boolean;
  // REQ-047 §2.3 — auto-materialisation metadata.
  user_overridden: boolean;
  derived_path: OverwinteringPath | null;
  dormancy_care_active: boolean;
  materialized_at: string | null;
  source_template_key: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/**
 * REQ-047 §2.3 — winter path derived from the hardiness traffic light
 * (invariant D5): `A` = in-situ dormancy with protection, `B` = relocated to a
 * winter quarter / tuber storage.
 */
export type OverwinteringPath = 'A' | 'B';

/**
 * REQ-047 §4.3 — winter-hardiness status of a plant instance (always HTTP 200,
 * mirrors the backend `PlantOverwinteringStatus`). Additive companion to the
 * profile read so the detail page can tell three states apart:
 *  - `has_profile=true` — a profile is materialised.
 *  - `has_profile=false` + `will_materialize=true` — no profile yet, but the
 *    ampel is yellow/red so one is auto-created at the autumn season transition.
 *  - `has_profile=false` + `hardiness_light='green'` — genuinely winter-hardy.
 * `hardiness_light=null` means the context is unknown (show a neutral text).
 * `site_overwinterable=false` means the plant sits on an indoor/protected site
 * (not in `OVERWINTERING_SITE_TYPES`): it is never materialised, so
 * `will_materialize` stays `false` regardless of the ampel and the UI explains
 * that no outdoor overwintering is due.
 */
export interface PlantOverwinteringStatus {
  has_profile: boolean;
  hardiness_light: WinterHardinessLight | null;
  will_materialize: boolean;
  site_overwinterable: boolean;
}

/**
 * REQ-047 §4.3 — partial override of an auto-materialised overwintering profile.
 * Any field the user sets flips `user_overridden` to `true` on the backend, so
 * the automation only fills remaining gaps afterwards.
 */
export type OverwinteringOverride = Partial<
  Omit<OverwinteringProfileCreate, 'plant_key' | 'planting_run_key'>
>;

export interface OverwinteringProfileCreate {
  plant_key?: string | null;
  planting_run_key?: string | null;
  hardiness_zone_min?: string | null;
  hardiness_rating: HardinessRating;
  winter_action: WinterAction;
  winter_action_month: number;
  spring_action?: SpringAction | null;
  spring_action_month?: number | null;
  winter_quarter_key?: string | null;
  winter_quarter_temp_min?: number | null;
  winter_quarter_temp_max?: number | null;
  winter_quarter_light?: WinterQuarterLight | null;
  winter_watering?: WinterWatering | null;
  storage_medium?: string | null;
  storage_check_interval_days?: number | null;
  tuber_status?: TuberStatus | null;
  notes?: string | null;
}

export type OverwinteringProfileUpdate = Partial<
  Omit<OverwinteringProfileCreate, 'plant_key' | 'planting_run_key'>
>;

export interface OverwinteringProfileAutoGenerate {
  plant_key?: string | null;
  planting_run_key?: string | null;
  species_key?: string | null;
  site_key?: string | null;
  frost_sensitivity?: FrostTolerance | null;
  species_zone?: string | null;
  site_zone?: string | null;
  winter_action_month?: number;
  spring_action_month?: number;
  winter_quarter_key?: string | null;
}

/** One red (must-relocate) plant in the dashboard hardiness overview. */
export interface WinterHardinessOverviewEntry {
  profile_key: string;
  plant_key: string | null;
  planting_run_key: string | null;
  hardiness_rating: HardinessRating;
  winter_action: WinterAction;
  /** Server-enriched, human-readable labels (#631) — all best-effort / nullable. */
  plant_name?: string | null;
  instance_id?: string | null;
  species_common_name?: string | null;
  species_scientific_name?: string | null;
  location_name?: string | null;
}

/**
 * REQ-022 §Dashboard-Widget "Winterschutz-Übersicht" — aggregate counts per
 * traffic-light colour plus the actionable red-plant list.
 */
export interface WinterHardinessOverview {
  green: number;
  yellow: number;
  red: number;
  total: number;
  red_plants: WinterHardinessOverviewEntry[];
}

// ── REQ-047 Season & overwintering automation ─────────────────────────────

/**
 * REQ-047 §2.2 — season state machine of an outdoor/greenhouse site.
 * Directed cycle: growing → pre_winter → winter_dormancy → pre_spring → growing.
 */
export type SeasonPhase = 'growing' | 'pre_winter' | 'winter_dormancy' | 'pre_spring';

/**
 * REQ-047 §1 — which cascade tier produced the current season state
 * (best-source-wins: live weather → climatological → calendar). Surfaced so the
 * dashboard can show whether a warning rests on real data or an estimate.
 */
export type SeasonTriggerTier = 'live' | 'climatological' | 'calendar';

/**
 * REQ-047 §2.1 — the per-site season state (mirrors `SeasonStateResponse`).
 */
export interface SeasonState {
  site_key: string;
  season_state_id: string;
  phase: SeasonPhase;
  trigger_tier: SeasonTriggerTier;
  /** i18n key for the natural-language trigger reason, e.g. `pages.season.trigger.frostForecast`. */
  trigger_reason_i18n_key: string;
  season_year: number | null;
  entered_phase_at: string | null;
  last_min_temp_c: number | null;
  /** ISO date of the next forecast frost (live tier only). */
  forecast_first_frost_date: string | null;
  /** Climatological frost termini (tier 2/3), format `MM-DD`. */
  estimated_first_frost_md: string | null;
  estimated_last_frost_md: string | null;
  evaluated_at: string | null;
}

/** REQ-047 §4.4 — aggregated season states across all outdoor sites of a tenant. */
export interface SeasonOverview {
  states: SeasonState[];
}

// ── REQ-046 Weather sources ───────────────────────────────────────────────

/** Coarse class used for the two-way UI switch (public service vs. HA). */
export type WeatherSourceKind = 'public' | 'home_assistant';

/** The two confirmed Home-Assistant weather modes. */
export type HaWeatherMode = 'weather_entity' | 'sensor_mapping';

/** Provenance classification of a produced weather record. */
export type WeatherDataKind = 'forecast' | 'observed' | 'reanalysis';

/** HA `sensor.*` field mapping (mode B). All fields optional; unmapped stays null. */
export interface HaSensorMapping {
  temp_min_entity?: string | null;
  temp_max_entity?: string | null;
  temp_current_entity?: string | null;
  humidity_entity?: string | null;
  precipitation_entity?: string | null;
  wind_speed_entity?: string | null;
  wind_gust_entity?: string | null;
  pressure_entity?: string | null;
}

/** Home-Assistant source configuration (mode A / mode B). */
export interface WeatherSourceHaConfig {
  mode: HaWeatherMode;
  weather_entity_id?: string | null;
  sensor_mapping?: HaSensorMapping | null;
}

/** Public-service source configuration in a request (plaintext api_key in). */
export interface WeatherSourcePublicConfigRequest {
  /** Plaintext OWM key. Empty / null / masked ("••••") means "unchanged". */
  api_key?: string | null;
  units_hint?: string | null;
}

/** Public-service source configuration in a response (masked out, AC-8). */
export interface WeatherSourcePublicConfigResponse {
  api_key_set: boolean;
  units_hint?: string | null;
}

/** One prioritised source entry in the request body. */
export interface WeatherSourceEntryRequest {
  source_name: string;
  kind: WeatherSourceKind;
  enabled: boolean;
  public_config?: WeatherSourcePublicConfigRequest | null;
  ha_config?: WeatherSourceHaConfig | null;
}

/** One prioritised source entry in the response body (masked). */
export interface WeatherSourceEntryResponse {
  source_name: string;
  kind: WeatherSourceKind;
  enabled: boolean;
  public_config?: WeatherSourcePublicConfigResponse | null;
  ha_config?: WeatherSourceHaConfig | null;
}

/** PUT body — the full prioritised source list for a site. */
export interface WeatherSourceConfigRequest {
  enabled: boolean;
  sources: WeatherSourceEntryRequest[];
}

/** GET response — the persisted, masked weather-source configuration. */
export interface WeatherSourceConfigResponse {
  site_key: string;
  enabled: boolean;
  sources: WeatherSourceEntryResponse[];
  updated_at?: string | null;
  updated_by?: string;
}

/** One selectable source advertised by the registry. */
export interface AvailableSourceItem {
  source_name: string;
  kind: string;
  requires_api_key: boolean;
}

/** `GET /weather-sources/available` response. */
export interface AvailableSourcesResponse {
  sources: AvailableSourceItem[];
  ha_token_set: boolean;
}

/** One preview row returned by the connection test. */
export interface WeatherTestPreviewItem {
  forecast_date: string;
  temp_min_c?: number | null;
  temp_max_c?: number | null;
  precipitation_mm?: number | null;
  wind_speed_kmh?: number | null;
  humidity_percent?: number | null;
  source: string;
  data_kind: string;
  is_current_conditions: boolean;
}

/** `POST /weather-sources/test` response (reachability + preview, AC-7). */
export interface WeatherTestResponse {
  reachable: boolean;
  preview: WeatherTestPreviewItem[];
  error?: string | null;
}

// ── Admin weather providers (REQ-046 follow-up, platform-admin) ───────────

/** Effective, masked config of one central public weather provider. */
export interface WeatherProviderInfo {
  source_name: string;
  enabled: boolean;
  base_url: string;
  attribution: string;
}

/** `GET /admin/weather-providers` — masked instance-wide provider config. */
export interface WeatherProvidersResponse {
  providers: WeatherProviderInfo[];
  openweathermap_global_api_key_set: boolean;
  fetch_timeout_s: number;
  default_public_source: string;
}

/**
 * `PUT /admin/weather-providers` payload. A `null`/omitted field is left
 * unchanged; the global OWM key follows the "unchanged on empty/masked" rule.
 */
export interface WeatherProvidersUpdate {
  open_meteo_enabled?: boolean | null;
  open_meteo_base_url?: string | null;
  dwd_enabled?: boolean | null;
  dwd_base_url?: string | null;
  openweathermap_enabled?: boolean | null;
  openweathermap_base_url?: string | null;
  openweathermap_global_api_key?: string | null;
  fetch_timeout_s?: number | null;
  default_public_source?: 'open-meteo' | 'dwd' | 'openweathermap' | null;
}

/** `POST /admin/weather-providers/{source_name}/test` response. */
export interface WeatherProviderTestResponse {
  reachable: boolean;
  preview: WeatherTestPreviewItem[];
  error?: string | null;
}

/**
 * One in-horizon daily forecast row for the per-site forecast widget
 * (Issue #392 — `GET /sites/{siteKey}/weather-forecast`). Carries the REQ-046
 * provenance (`source` / `data_kind`) so the widget can render the
 * `WeatherProvenanceBadge`.
 */
export interface SiteWeatherForecastDay {
  forecast_date: string;
  temp_min_c?: number | null;
  temp_max_c?: number | null;
  precipitation_mm?: number | null;
  wind_speed_kmh?: number | null;
  humidity_percent?: number | null;
  weather_code?: string | null;
  source: string;
  data_kind: string;
}

/**
 * `GET /sites/{siteKey}/weather-forecast` response — per-site daily forecast plus
 * the proactive frost early-warning summary (Issue #392). Graceful: when no
 * forecast source is available `forecasts` is empty and every `forecast_*`
 * summary field is `null` (never a 500).
 */
export interface SiteWeatherForecastResponse {
  site_key: string;
  forecasts: SiteWeatherForecastDay[];
  forecast_frost_warning?: boolean | null;
  forecast_min_temperature?: number | null;
  forecast_expected_date?: string | null;
  forecast_source?: string | null;
}

/**
 * REQ-041 — one long-term climate-normal record for a site (one per source).
 * `GET /sites/{siteKey}/climate-normals`. The twelve `monthly_*` arrays are
 * January…December (empty when the source did not report that series). Each
 * record carries its source's CC-BY `attribution` string for UI visibility.
 */
export interface ClimateNormal {
  source: string;
  attribution: string;
  period_start_year?: number | null;
  period_end_year?: number | null;
  monthly_temp_min_c: number[];
  monthly_temp_max_c: number[];
  monthly_temp_avg_c: number[];
  monthly_precip_mm: number[];
  monthly_solar_mj_m2: number[];
  coldest_month_min_c?: number | null;
  annual_temp_avg_c?: number | null;
  annual_precip_mm?: number | null;
  fetched_at: string;
}

/**
 * `GET /sites/{siteKey}/climate-normals` response — the site's climate normals
 * for the "Klima am Standort" section. Graceful: an empty `normals` list means
 * no source has populated normals for the site yet (never a 500).
 */
export interface SiteClimateResponse {
  site_key: string;
  normals: ClimateNormal[];
}

/** One HA entity offered by the HA entity pickers. */
export interface HaEntityItem {
  entity_id: string;
  friendly_name: string;
  state?: string | null;
  unit_of_measurement?: string | null;
  device_class?: string | null;
}

// ── REQ-031 KI-Assistent ────────────────────────────────────────────

/** ADR-002 confidence marker for how well a species maps onto the KB. */
export type AiConfidence = 'high' | 'medium' | 'low' | 'none';

/** A cited knowledge chunk attached to a KI answer (Quellenpflicht). */
export interface AiSourceRef {
  source_key: string;
  source_type: string;
  title: string;
  score: number;
  language: string;
}

/** The common KI answer envelope rendered by `<AIResponse>` (§5.5). */
/**
 * Issue #685 — public KI-Assistent availability payload.
 *
 * Mirrors the backend operator flag (`AI_FEATURES_ENABLED`). Used to hide the
 * KI-Assistent nav entry and degrade its page when AI is off cluster-wide.
 */
export interface AiStatus {
  available: boolean;
}

export interface AiResponse {
  answer_text: string;
  sources: AiSourceRef[];
  language: string;
  language_mismatch_warning: boolean;
  uses_tenant_data: boolean;
  uses_cloud_provider: boolean;
  confidence: AiConfidence;
  fallback_species?: string | null;
  cultivar_hint?: string | null;
  model_name: string;
  provider_type: string;
  kb_version?: string | null;
  generated_at?: string | null;
}

/** A single tip card. */
export interface AiTipCard {
  key?: string | null;
  context_type: string;
  context_key: string;
  tip_type: string;
  priority: string;
  title: string;
  body: string;
  action_url?: string | null;
  sources: AiSourceRef[];
  language: string;
  language_mismatch_warning: boolean;
  uses_tenant_data: boolean;
  confidence: AiConfidence;
  model_name: string;
  generated_at?: string | null;
}

export interface AiTipListResponse {
  tips: AiTipCard[];
}

export interface AiExplainRequest {
  subject_type: 'task' | 'reminder' | 'phase_transition' | 'feeding_event';
  subject_key: string;
  question_template_id: string;
  language?: 'de' | 'en';
}

export interface AiConversationSummary {
  key?: string | null;
  title?: string | null;
  context_type: string;
  context_key?: string | null;
  message_count: number;
  updated_at?: string | null;
}

// ── REQ-035 KI terminology glossary ─────────────────────────────────────

export type GlossaryExpertiseLevel = 'beginner' | 'intermediate' | 'expert';

/** A single row of the glossary term browser (§3.1 `/terms`). */
export interface GlossaryTermSummary {
  slug: string;
  label: string;
  category: string;
}

/** A related-term reference rendered as a clickable chip (§3.4). */
export interface GlossaryRelatedTerm {
  slug: string;
  label: string;
}

/** The full `get_term` response envelope (§3.4). */
export interface GlossaryTermAnswer {
  slug: string;
  label: string;
  long_label: string;
  category: string;
  answer_text: string;
  expertise_level: GlossaryExpertiseLevel;
  language: string;
  language_mismatch_warning: boolean;
  sources: AiSourceRef[];
  related_terms: GlossaryRelatedTerm[];
  is_fallback: boolean;
  model_name: string;
  provider_type: string;
  uses_tenant_data: boolean;
  uses_cloud_provider: boolean;
  kb_version?: string | null;
  generated_at?: string | null;
}

// ── REQ-036 KI-Diagnose-Assistent ───────────────────────────────────────

/** One curated symptom offered by the diagnosis wizard's first step. */
export interface DiagnosisSymptom {
  slug: string;
  category: string;
  label: string;
  common_causes_hint: string;
  applicable_phases: string[];
}

export interface DiagnosisSymptomListResponse {
  symptoms: DiagnosisSymptom[];
}

/** A REQ-010 treatment suggested for a matched pest (bridge, read-only). */
export interface DiagnosisMatchedTreatment {
  key: string;
  name: string;
  name_de?: string | null;
  treatment_type: string;
  safety_interval_days: number;
  has_karenz: boolean;
  detail_url: string;
}

/** An enriched top-N diagnosis candidate (IPM-bridged). */
export interface DiagnosisCandidate {
  rank: number;
  name: string;
  scientific_name?: string | null;
  category: string;
  confidence: number;
  confidence_level: AiConfidence;
  explanation: string;
  recommended_actions: string[];
  matched_pest_key?: string | null;
  matched_pest_detail_url?: string | null;
  matched_disease_key?: string | null;
  matched_disease_detail_url?: string | null;
  matched_treatments: DiagnosisMatchedTreatment[];
}

/** The top-3 diagnosis envelope rendered inside `<AIResponse>`. */
export interface DiagnosisResult {
  candidates: DiagnosisCandidate[];
  answer_summary: string;
  sources: AiSourceRef[];
  language: string;
  uses_tenant_data: boolean;
  uses_cloud_provider: boolean;
  confidence: AiConfidence;
  model_name: string;
  provider_type: string;
  kb_version?: string | null;
  status: 'ok' | 'knowledge_service_error' | 'error';
  error_class?: string | null;
}

export interface DiagnoseRequest {
  symptom_slugs: string[];
  extra_notes?: string | null;
  plant_instance_key?: string | null;
  photo_ref?: string | null;
  language?: 'de' | 'en';
}

// ── REQ-026 Aquaponics ──────────────────────────────────────────────────

export type AquaponicSystemType = 'media_bed' | 'dwc' | 'nft' | 'hybrid' | 'wicking_bed';

export type CyclingStatus = 'new' | 'cycling' | 'cycled' | 'dormant';

export type TemperatureZone = 'coldwater' | 'temperate' | 'warmwater';

export type BiofilterType = 'media_bed_integrated' | 'mbbr' | 'trickle' | 'fluidized_bed';

export type ClarifierType = 'swirl' | 'settling' | 'drum' | 'screen';

export type FishFeedType = 'pellet' | 'flake' | 'live' | 'frozen' | 'paste';

export type FishFeedingResponse = 'eager' | 'normal' | 'reduced' | 'refused';

export type FishFeedCategory = 'carnivore' | 'omnivore' | 'herbivore';

export type AquaponicSupplementType =
  'fe_dtpa' | 'fe_eddha' | 'koh' | 'k2co3' | 'ca_oh_2' | 'mgso4' | 'mnso4' | 'h3bo3' | 'znso4';

export type WaterTestSource = 'manual' | 'sensor' | 'test_kit';

export type WaterQualitySeverity = 'ok' | 'info' | 'warning' | 'critical';

export interface AquaponicSystem {
  key: string;
  name: string;
  system_type: AquaponicSystemType;
  total_volume_liters: number;
  grow_area_m2: number;
  cycling_status: CyclingStatus;
  cycling_start_date?: string | null;
  cycled_since?: string | null;
  biofilter_type?: BiofilterType | null;
  biofilter_volume_liters?: number | null;
  has_clarifier: boolean;
  clarifier_type?: ClarifierType | null;
  has_mineralization: boolean;
  has_vermicompost: boolean;
  daily_feed_target_g: number;
  turnover_rate_per_hour?: number | null;
  outdoor: boolean;
  backup_power: boolean;
  ph_target_min: number;
  ph_target_max: number;
  notes?: string | null;
}

export interface AquaponicSystemCreate {
  name: string;
  system_type: AquaponicSystemType;
  total_volume_liters: number;
  grow_area_m2: number;
  biofilter_type?: BiofilterType | null;
  biofilter_volume_liters?: number | null;
  has_clarifier?: boolean;
  clarifier_type?: ClarifierType | null;
  has_mineralization?: boolean;
  has_vermicompost?: boolean;
  daily_feed_target_g?: number;
  outdoor?: boolean;
  backup_power?: boolean;
  ph_target_min?: number;
  ph_target_max?: number;
  notes?: string | null;
}

export type AquaponicSystemUpdate = Partial<AquaponicSystemCreate>;

export interface FishStock {
  key: string;
  system_key: string;
  name: string;
  species_key: string;
  count: number;
  initial_count: number;
  avg_weight_g: number;
  total_biomass_kg: number;
  stocking_date: string;
  mortality_count: number;
  last_weighed_at?: string | null;
  notes?: string | null;
}

export interface FishStockCreate {
  name: string;
  species_key: string;
  count: number;
  avg_weight_g: number;
  stocking_date: string;
  notes?: string | null;
}

export interface WaterTest {
  key: string;
  system_key: string;
  tested_at?: string | null;
  ph: number;
  ammonia_tan_mgl: number;
  nitrite_mgl: number;
  nitrate_mgl: number;
  temperature_c: number;
  dissolved_oxygen_mgl?: number | null;
  kh_dh?: number | null;
  gh_dh?: number | null;
  iron_ppm?: number | null;
  potassium_ppm?: number | null;
  calcium_ppm?: number | null;
  magnesium_ppm?: number | null;
  phosphate_ppm?: number | null;
  free_ammonia_mgl: number;
  source: WaterTestSource;
  notes?: string | null;
}

export interface WaterTestCreate {
  ph: number;
  ammonia_tan_mgl: number;
  nitrite_mgl: number;
  nitrate_mgl: number;
  temperature_c: number;
  dissolved_oxygen_mgl?: number | null;
  kh_dh?: number | null;
  gh_dh?: number | null;
  iron_ppm?: number | null;
  potassium_ppm?: number | null;
  calcium_ppm?: number | null;
  magnesium_ppm?: number | null;
  phosphate_ppm?: number | null;
  source?: WaterTestSource;
  notes?: string | null;
}

export interface WaterQualityEvaluation {
  parameter: string;
  value: number;
  limit: number;
  severity: WaterQualitySeverity;
  message_de: string;
  message_en: string;
}

export interface CyclingProgress {
  status: CyclingStatus;
  progress_percent: number;
  stable_days: number;
  days_required: number;
  estimated_completion?: string | null;
  phase_description_de: string;
  phase_description_en: string;
}

export interface FeedingRecommendation {
  recommended_g: number;
  base_rate_percent: number;
  temperature_factor: number;
  cycling_factor: number;
  species_name: string;
  biomass_kg: number;
  water_temp_c: number;
  notes: string[];
}

export interface NitrogenCyclePoint {
  tested_at?: string | null;
  ammonia_tan_mgl: number;
  free_ammonia_mgl: number;
  nitrite_mgl: number;
  nitrate_mgl: number;
  ph: number;
  temperature_c: number;
}

export interface FishSpecies {
  key: string;
  scientific_name: string;
  common_name_de: string;
  common_name_en: string;
  temperature_zone: TemperatureZone;
  temperature_optimal_min_c: number;
  temperature_optimal_max_c: number;
  max_tan_mgl: number;
  max_nitrite_mgl: number;
  max_nitrate_mgl: number;
  feed_type: FishFeedCategory;
  max_stocking_density_kg_per_1000l: number;
  notes_de?: string | null;
}

// ── REQ-018 Environment control / actuators ──────────────────────────────

export type ActuatorType =
  | 'light'
  | 'exhaust_fan'
  | 'circulation_fan'
  | 'heater'
  | 'cooler'
  | 'humidifier'
  | 'dehumidifier'
  | 'co2_doser'
  | 'irrigation_valve'
  | 'pump'
  | 'dosing_pump'
  | 'chiller'
  | 'air_pump'
  | 'uv_sterilizer'
  | 'shade_screen'
  | 'roof_vent'
  | 'energy_screen'
  | 'fogger'
  | 'generic_switch';

export type ActuatorCapability =
  | 'on_off'
  | 'dimmable'
  | 'speed_control'
  | 'temperature_setpoint'
  | 'timer'
  | 'spectrum_control'
  | 'volume_dosing';

export type ActuatorProtocol = 'home_assistant' | 'mqtt' | 'manual';

export type ControlEventSource =
  'schedule' | 'rule' | 'phase_change' | 'manual' | 'safety' | 'fallback_task';

export type EmergencyStopScenario = 'water_leak' | 'co2_leak' | 'fire_alarm';

export interface Actuator {
  key: string;
  tenant_key: string;
  location_key: string;
  name: string;
  actuator_type: ActuatorType;
  protocol: ActuatorProtocol;
  ha_entity_id: string | null;
  mqtt_command_topic: string | null;
  mqtt_state_topic: string | null;
  capabilities: ActuatorCapability[];
  min_value: number | null;
  max_value: number | null;
  unit: string | null;
  current_state: string | null;
  current_value: number | null;
  last_state_change: string | null;
  is_online: boolean;
  last_seen: string | null;
  power_watts: number | null;
  fail_safe_state: string | null;
  fail_safe_value: number | null;
  conflict_group: string | null;
  installed_on: string | null;
  notes: string | null;
}

export interface ActuatorCreate {
  name: string;
  actuator_type: ActuatorType;
  protocol: ActuatorProtocol;
  ha_entity_id?: string | null;
  mqtt_command_topic?: string | null;
  power_watts?: number | null;
  notes?: string | null;
}

export interface ControlEvent {
  key: string;
  actuator_key: string;
  location_key: string;
  timestamp: string | null;
  event_source: ControlEventSource;
  command: string;
  value: number | null;
  previous_state: string | null;
  new_state: string;
  success: boolean;
  error_message: string | null;
  sensor_reading_at_trigger: number | null;
}

export interface ActuatorState {
  actuator_key: string;
  current_state: string | null;
  current_value: number | null;
  is_online: boolean;
  last_state_change: string | null;
  has_override: boolean;
}

export interface EmergencyStopResult {
  scenario: string;
  stopped: string[];
  forced_on: string[];
  /** Actuators the backend could not stop/force (per-device isolation — one
   * dispatch failure never aborts the rest of the emergency stop). The UI
   * MUST surface these instead of silently reporting a full success. */
  failed: string[];
}

// ── REQ-016 InvenTree integration (optional) ────────────────────────────

export type EquipmentType =
  | 'tool'
  | 'consumable'
  | 'sensor'
  | 'lighting'
  | 'pump'
  | 'filter'
  | 'container'
  | 'cleaning_agent'
  | 'other';

export type EquipmentStatus = 'active' | 'maintenance' | 'stored' | 'defective' | 'retired';

export type StockTransactionType = 'remove' | 'add' | 'count';

export type StockTransactionStatus = 'pending' | 'synced' | 'failed';

export interface Equipment {
  key: string;
  name: string;
  equipment_type: EquipmentType;
  status: EquipmentStatus;
  brand?: string | null;
  model?: string | null;
  serial_number?: string | null;
  purchase_date?: string | null;
  warranty_until?: string | null;
  location_key?: string | null;
  inventree_part_id?: number | null;
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface EquipmentCreate {
  name: string;
  equipment_type: EquipmentType;
  status?: EquipmentStatus;
  brand?: string | null;
  model?: string | null;
  serial_number?: string | null;
  location_key?: string | null;
  inventree_part_id?: number | null;
  notes?: string | null;
}

export type EquipmentUpdate = Partial<EquipmentCreate>;

export interface InvenTreeConnection {
  key: string;
  name: string;
  base_url: string;
  is_active: boolean;
  verify_ssl: boolean;
  api_token_set: boolean;
  sync_interval_minutes: number;
  push_interval_minutes: number;
  last_health_check_at?: string | null;
  last_health_check_ok?: boolean | null;
  last_stock_sync_at?: string | null;
  last_push_at?: string | null;
}

export interface InvenTreeConnectionCreate {
  name: string;
  base_url: string;
  api_token: string;
  is_active?: boolean;
  verify_ssl?: boolean;
}

export interface InvenTreeReference {
  key: string;
  entity_collection: string;
  entity_key: string;
  inventree_part_id: number;
  inventree_part_name?: string | null;
  cached_stock?: number | null;
  cached_stock_unit?: string | null;
  auto_deduct: boolean;
}

export interface StockTransaction {
  key: string;
  reference_key: string;
  inventree_part_id: number;
  transaction_type: StockTransactionType;
  quantity: number;
  unit: string;
  reason: string;
  status: StockTransactionStatus;
  retry_count: number;
  synced_at?: string | null;
  created_at?: string | null;
}

// ── REQ-017 Propagation / lineage ────────────────────────────────────────────

/** Event-level propagation method (REQ-017), distinct from the species-level
 *  `PropagationMethod` vocabulary above. */
export type PropagationEventMethod =
  'clone' | 'seed' | 'cutting' | 'graft' | 'division' | 'layering' | 'offset' | 'other';

export type PropagationEventStatus =
  'in_progress' | 'rooted' | 'transplanted' | 'completed' | 'failed';

export type GraftCompatibilityLevel = 'compatible' | 'possibly_compatible' | 'incompatible';

export interface PropagationEvent {
  _key?: string;
  method: PropagationEventMethod;
  status: PropagationEventStatus;
  parent_plant_keys: string[];
  child_plant_keys: string[];
  species_key?: string | null;
  cultivar_key?: string | null;
  protocol_key?: string | null;
  batch_key?: string | null;
  quantity: number;
  survived_count?: number | null;
  success_rate?: number | null;
  callus_observed_at?: string | null;
  roots_observed_at?: string | null;
  transplant_ready_at?: string | null;
  failure_reasons: string[];
  happened_at?: string | null;
  notes?: string | null;
}

export interface PropagationEventCreate {
  method: PropagationEventMethod;
  parent_plant_keys: string[];
  child_plant_keys: string[];
  species_key?: string | null;
  quantity: number;
  notes?: string | null;
}

export interface LineageNode {
  key?: string | null;
  instance_id?: string | null;
  plant_name?: string | null;
  species_key?: string | null;
}

export interface LineageResponse {
  plant_key: string;
  paths: string[][];
  ancestors: LineageNode[];
}

export interface DescendantsResponse {
  plant_key: string;
  descendants: LineageNode[];
}

export interface GraftCompatibilityResponse {
  scion_key: string;
  rootstock_key: string;
  scion_species_key: string;
  rootstock_species_key: string;
  compatible: boolean;
  level: GraftCompatibilityLevel;
  same_genus: boolean;
  same_family: boolean;
  message: string;
}
