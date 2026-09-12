from fastapi import APIRouter, Depends

from app.api.v1.calculations.schemas import (
    GDDRequest,
    GDDResponse,
    PhotoperiodTransitionRequest,
    PhotoperiodTransitionResponse,
    SlotCapacityRequest,
    SlotCapacityResponse,
    SunTimesRangeRequest,
    SunTimesRequest,
    SunTimesResponse,
    VernalizationRequest,
    VernalizationResponse,
    VPDRequest,
    VPDResponse,
)
from app.common.auth import get_current_user
from app.common.openapi_responses import AUTH_RESPONSES
from app.domain.calculators.gdd_calculator import calculate_accumulated_gdd
from app.domain.calculators.photoperiod_calculator import calculate_dli, calculate_transition_schedule
from app.domain.calculators.slot_capacity_calculator import (
    calculate_max_capacity,
    calculate_optimal_range,
    calculate_plants_per_m2,
)
from app.domain.calculators.sun_calculator import calculate_sun_times, calculate_sun_times_range
from app.domain.calculators.vpd_calculator import calculate_vpd, classify_vpd

# GATED AT THE ROUTER, NOT AT EACH HANDLER (#1402).
#
# All seven operations here answered an UNAUTHENTICATED caller until #1402. The
# router carried no ``dependencies=``, no handler named an auth parameter, and
# ``main.py`` registers no auth middleware (security headers, request id, CORS).
# The #1353 sweep did not report them because both of its selectors key on the
# PRESENCE of a specific weak dependency — ``ctx is get_current_tenant`` for the
# tenant half, ``get_current_user in dependencies`` for the admin half — and a
# route carrying no dependency at all matches neither. That hole is closed in
# ``tests/unit/api/test_write_route_gates.py`` in the same change.
#
# The gate sits on the ROUTER so a new calculator inherits it. Putting it on each
# handler is the opt-in-at-the-call-site shape that produced #948, #1385 and
# #1399: seven siblings were gated, the eighth was added later and was not.
#
# ``get_current_user`` and not ``get_current_tenant``: these are pure functions of
# the request body — VPD from temperature and humidity, GDD from a series, sun
# times from coordinates — mounted globally at ``/api/v1/calculations`` with no
# tenant in the path. They read no tenant data, so a tenant resolution would be
# an invention; what they needed was to stop being reachable by anyone at all.
# ``responses=AUTH_RESPONSES`` because the gate has to appear in the CONTRACT and
# not only in the code: without it the OpenAPI document describes seven
# operations that can answer 401 and documents neither 401 nor 403, so a
# generated client and ``docs/*/api/`` show the refusal as undocumented. Every
# other auth-requiring router in the tree declares it (``imports``,
# ``companion_planting``, ``hardiness_zones``, ``knowledge``, ``mcp``,
# ``tenant_scoped``); ``nutrient_calculations`` inherits it from
# ``tenant_scoped_router``, which is why only this file needed it.
router = APIRouter(
    prefix="/calculations",
    tags=["calculations"],
    dependencies=[Depends(get_current_user)],
    responses=AUTH_RESPONSES,
)


@router.post("/vpd", response_model=VPDResponse)
def calc_vpd(body: VPDRequest):
    """Compute the vapour-pressure deficit and classify it for the given phase."""
    vpd = calculate_vpd(body.temp_c, body.humidity_percent)
    status, recommendation = classify_vpd(vpd, body.phase)
    return VPDResponse(vpd_kpa=round(vpd, 4), status=status, recommendation=recommendation)


@router.post("/gdd", response_model=GDDResponse)
def calc_gdd(body: GDDRequest):
    """Accumulate growing degree days from a series of daily temperatures."""
    gdd = calculate_accumulated_gdd(body.daily_temps, body.base_temp_c)
    return GDDResponse(accumulated_gdd=round(gdd, 2), days_counted=len(body.daily_temps))


@router.post("/photoperiod-transition", response_model=PhotoperiodTransitionResponse)
def calc_photoperiod(body: PhotoperiodTransitionRequest):
    """Build a gradual photoperiod-transition schedule with the resulting DLI per day."""
    schedule = calculate_transition_schedule(
        body.current_hours, body.target_hours, body.transition_days, body.lights_on_time
    )
    for entry in schedule:
        entry["dli"] = round(calculate_dli(body.ppfd, entry["photoperiod_hours"]), 2)
    return {"schedule": schedule}


@router.post("/sun-times", response_model=SunTimesResponse)
def calc_sun_times(body: SunTimesRequest):
    """Compute sunrise, sunset and twilight times for a location and date."""
    result = calculate_sun_times(body.latitude, body.longitude, body.date, body.timezone)
    return SunTimesResponse(**result)


@router.post("/sun-times-range", response_model=list[SunTimesResponse])
def calc_sun_times_range(body: SunTimesRangeRequest):
    """Compute sun times for each day across a date range."""
    results = calculate_sun_times_range(body.latitude, body.longitude, body.start_date, body.end_date, body.timezone)
    return [SunTimesResponse(**r) for r in results]


@router.post("/slot-capacity", response_model=SlotCapacityResponse)
def calc_slot_capacity(body: SlotCapacityRequest):
    """Compute maximum and optimal plant capacity for a growing area."""
    max_cap = calculate_max_capacity(body.area_m2, body.plant_spacing_cm)
    opt_range = calculate_optimal_range(body.area_m2, body.plant_spacing_cm)
    ppm2 = calculate_plants_per_m2(body.plant_spacing_cm)
    return SlotCapacityResponse(max_capacity=max_cap, optimal_range=opt_range, plants_per_m2=round(ppm2, 2))


@router.post("/vernalization", response_model=VernalizationResponse)
def calc_vernalization(body: VernalizationRequest):
    """Compute vernalization progress from accumulated cold days."""
    from app.domain.engines.vernalization_tracker import VernalizationTracker

    tracker = VernalizationTracker()
    result = tracker.calculate_vernalization_progress(body.cold_days_accumulated, body.required_min_days)
    return VernalizationResponse(
        progress_percent=result["progress_percent"],
        days_remaining=result["days_remaining"],
        is_complete=result["is_complete"],
    )
