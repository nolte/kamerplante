"""REQ-013 §2 — SuccessionPlanService CRUD + run generation (Szenario 4)."""

from datetime import date

import pytest

from app.common.enums import SuccessionPlanStatus
from app.common.exceptions import NotFoundError, ValidationError
from app.domain.models.planting_run import PlantingRun
from app.domain.models.site import Location, Site
from app.domain.models.succession_plan import SuccessionPlan
from app.domain.services.succession_plan_service import SuccessionPlanService

TENANT = "tenant_lisa"


class _FakeSuccessionRepo:
    def __init__(self) -> None:
        self._store: dict[str, SuccessionPlan] = {}
        self._seq = 0
        self.run_edges: list[tuple[str, str]] = []
        self.location_edges: list[tuple[str, str]] = []

    def get_all(self, offset=0, limit=50, tenant_key=None, *, all_tenants=False):
        items = [p for p in self._store.values() if p.tenant_key == tenant_key]
        return items[offset : offset + limit], len(items)

    def get_by_key(self, key):
        return self._store.get(key)

    def get_or_raise(self, key):
        plan = self._store.get(key)
        if plan is None:
            raise NotFoundError("SuccessionPlan", key)
        return plan

    def create(self, plan: SuccessionPlan) -> SuccessionPlan:
        self._seq += 1
        key = f"sp{self._seq}"
        stored = plan.model_copy(update={"key": key})
        self._store[key] = stored
        return stored

    def update(self, key, plan: SuccessionPlan) -> SuccessionPlan:
        stored = plan.model_copy(update={"key": key})
        self._store[key] = stored
        return stored

    def delete(self, key) -> bool:
        return self._store.pop(key, None) is not None

    def link_plan_to_run(self, plan_key, run_key) -> None:
        self.run_edges.append((plan_key, run_key))

    def link_plan_to_location(self, plan_key, location_key) -> None:
        self.location_edges.append((plan_key, location_key))

    def get_run_keys_for_plan(self, plan_key) -> list[str]:
        return [rk for pk, rk in self.run_edges if pk == plan_key]


class _FakeRunService:
    """Echoes back created runs with a fresh key; records the entries per run."""

    def __init__(self) -> None:
        self._seq = 0
        self.created_runs: list[PlantingRun] = []
        self.created_entries: list[list] = []

    def create_run(self, run: PlantingRun, entries=None) -> PlantingRun:
        self._seq += 1
        created = run.model_copy(update={"key": f"run{self._seq}"})
        self.created_runs.append(created)
        self.created_entries.append(entries or [])
        return created


class _FakeSiteRepo:
    """Minimal site repo exposing only ``get_location_by_key`` (ownership guard)."""

    """A site repository that stores what the write path actually stores.

    ``Location`` rows are built with no ``tenant_key`` — the field exists on the
    model and the application never fills it (#1397), because ``LocationCreate``
    may not carry one (#1000) and ``create_location`` does
    ``Location(**body.model_dump())``. A double that invents the value makes a
    positive test certify nothing: the real repository would hand the service a
    location whose ``tenant_key`` is ``""``, and only the double's version passes
    an ownership check written against that field.

    The tenant lives on the parent ``Site``, so this double serves sites too.
    """

    def __init__(self, locations: dict[str, Location] | None = None) -> None:
        self._locations = locations or {}
        self._sites: dict[str, Site] = {}
        for location in self._locations.values():
            self._register_site(location)

    def _register_site(self, location: Location) -> None:
        if location.site_key and location.site_key not in self._sites:
            self._sites[location.site_key] = Site(
                _key=location.site_key,
                tenant_key=_SITE_TENANTS[location.site_key],
                name=location.site_key,
                site_type="indoor",
            )

    def get_location_by_key(self, key):
        return self._locations.get(key)

    def get_site_by_key(self, key):
        return self._sites.get(key)


#: Which tenant each fixture site belongs to. Held beside the factory rather than
#: on the ``Location`` so the double cannot drift back into carrying the tenant on
#: the row itself.
_SITE_TENANTS: dict[str, str] = {}


def _location(key: str, tenant_key: str) -> Location:
    """A location as the write path stores one: no ``tenant_key``, a parent site.

    ``tenant_key`` stays in the signature because that is what the caller means —
    it is recorded on the site this location hangs under, which is where the
    application reads it from.
    """
    site_key = f"site_{tenant_key}"
    _SITE_TENANTS[site_key] = tenant_key
    return Location(_key=key, name=key, area_m2=1.0, site_key=site_key)


def _plan(**overrides) -> SuccessionPlan:
    data = {
        "tenant_key": TENANT,
        "name": "Salat-Staffel Beet C 2026",
        "species_key": "species_lactuca_sativa",
        "cultivar_key": "cultivar_lollo_rosso",
        "interval_days": 21,
        "start_date": date(2026, 4, 1),
        "end_date": date(2026, 8, 31),
        "plants_per_batch": 12,
        "location_key": "loc_beet_c",
    }
    data.update(overrides)
    return SuccessionPlan(**data)


def _service():
    repo = _FakeSuccessionRepo()
    run_service = _FakeRunService()
    return SuccessionPlanService(repo, run_service), repo, run_service


class TestCrud:
    def test_create_sets_defaults_and_total_batches(self):
        service, _repo, _rs = _service()
        created = service.create_plan(_plan())
        assert created.status == SuccessionPlanStatus.PLANNED
        assert created.total_batches == 8
        assert created.completed_batches == 0

    def test_get_plan_enforces_tenant(self):
        service, _repo, _rs = _service()
        created = service.create_plan(_plan())
        with pytest.raises(NotFoundError):
            service.get_plan(created.key, tenant_key="other")

    def test_update_recomputes_total_batches(self):
        service, _repo, _rs = _service()
        created = service.create_plan(_plan())
        updated = service.update_plan(created.key, {"interval_days": 42}, tenant_key=TENANT)
        # 152-day window / 42 → 3 + 1 = 4 batches.
        assert updated.total_batches == 4

    def test_update_ignores_unknown_fields(self):
        service, _repo, _rs = _service()
        created = service.create_plan(_plan())
        updated = service.update_plan(created.key, {"tenant_key": "hijack", "notes": "spring"}, tenant_key=TENANT)
        assert updated.tenant_key == TENANT
        assert updated.notes == "spring"

    def test_delete_plan(self):
        service, _repo, _rs = _service()
        created = service.create_plan(_plan())
        assert service.delete_plan(created.key, tenant_key=TENANT) is True


class TestGenerateRuns:
    def test_generate_creates_eight_runs_and_edges(self):
        service, repo, run_service = _service()
        created = service.create_plan(_plan())

        plan, runs = service.generate_runs(created.key, tenant_key=TENANT)

        assert len(runs) == 8
        assert len(run_service.created_runs) == 8
        # one has_succession_plan edge per run + one succession_at edge.
        assert len(repo.run_edges) == 8
        assert repo.location_edges == [(created.key, "loc_beet_c")]
        # plan bookkeeping updated.
        assert plan.total_batches == 8
        assert plan.completed_batches == 8
        assert plan.status == SuccessionPlanStatus.ACTIVE

    def test_generated_runs_carry_sequence_and_entry(self):
        service, _repo, run_service = _service()
        created = service.create_plan(_plan())

        _plan_out, runs = service.generate_runs(created.key, tenant_key=TENANT)

        assert [r.succession_sequence for r in runs] == list(range(1, 9))
        assert all(r.succession_total == 8 for r in runs)
        assert runs[0].planned_start_date == date(2026, 4, 1)
        assert runs[1].planned_start_date == date(2026, 4, 22)
        # each run received exactly one entry with the plan's species.
        for entries in run_service.created_entries:
            assert len(entries) == 1
            assert entries[0].species_key == "species_lactuca_sativa"
            assert entries[0].quantity == 12


class TestGenerateNextRun:
    def test_generate_next_advances_one_batch(self):
        service, repo, run_service = _service()
        created = service.create_plan(_plan())

        plan1, run1 = service.generate_next_run(created.key, tenant_key=TENANT)
        assert run1 is not None
        assert run1.succession_sequence == 1
        assert plan1.completed_batches == 1
        assert plan1.status == SuccessionPlanStatus.ACTIVE

        plan2, run2 = service.generate_next_run(created.key, tenant_key=TENANT)
        assert run2 is not None
        assert run2.succession_sequence == 2
        assert plan2.completed_batches == 2
        assert len(repo.run_edges) == 2

    def test_generate_next_returns_none_when_complete(self):
        service, _repo, _rs = _service()
        created = service.create_plan(_plan(end_date=date(2026, 4, 1)))  # single batch

        _p1, run1 = service.generate_next_run(created.key, tenant_key=TENANT)
        assert run1 is not None

        plan2, run2 = service.generate_next_run(created.key, tenant_key=TENANT)
        assert run2 is None
        assert plan2.completed_batches == 1


class TestGenerateIdempotency:
    """Befund 1 — repeated generation must not create duplicate runs/edges."""

    def test_generate_twice_still_eight_runs(self):
        service, repo, run_service = _service()
        created = service.create_plan(_plan())

        _p1, first = service.generate_runs(created.key, tenant_key=TENANT)
        plan2, second = service.generate_runs(created.key, tenant_key=TENANT)

        assert len(first) == 8
        assert second == []  # no-op on the second call
        assert len(run_service.created_runs) == 8
        assert len(repo.run_edges) == 8  # one edge per unique run
        assert plan2.completed_batches == 8
        assert repo.location_edges == [(created.key, "loc_beet_c")]

    def test_generate_next_then_generate_no_duplicates(self):
        service, repo, run_service = _service()
        created = service.create_plan(_plan())

        service.generate_next_run(created.key, tenant_key=TENANT)  # batch 1
        service.generate_next_run(created.key, tenant_key=TENANT)  # batch 2
        plan, rest = service.generate_runs(created.key, tenant_key=TENANT)

        assert len(rest) == 6  # batches 3..8
        assert [r.succession_sequence for r in rest] == list(range(3, 9))
        assert len(run_service.created_runs) == 8
        assert len(repo.run_edges) == 8
        assert plan.completed_batches == 8


class TestUpdateDateValidation:
    """Befund 2 — an inverted merged date range must raise a 422 domain error."""

    def test_update_start_after_stored_end_raises_validation_error(self):
        service, _repo, _rs = _service()
        created = service.create_plan(_plan())  # end_date 2026-08-31
        with pytest.raises(ValidationError):
            service.update_plan(created.key, {"start_date": date(2026, 12, 1)}, tenant_key=TENANT)

    def test_update_end_before_stored_start_raises_validation_error(self):
        service, _repo, _rs = _service()
        created = service.create_plan(_plan())  # start_date 2026-04-01
        with pytest.raises(ValidationError):
            service.update_plan(created.key, {"end_date": date(2026, 1, 1)}, tenant_key=TENANT)


class TestLocationOwnership:
    """Befund 3 — a foreign location_key must be rejected before persistence."""

    def _service_with_site(self, site_repo):
        repo = _FakeSuccessionRepo()
        run_service = _FakeRunService()
        service = SuccessionPlanService(repo, run_service, site_repo=site_repo)
        return service, repo, run_service

    def test_create_with_foreign_location_rejected(self):
        site_repo = _FakeSiteRepo({"loc_foreign": _location("loc_foreign", "tenant_other")})
        service, _repo, _rs = self._service_with_site(site_repo)
        with pytest.raises(NotFoundError):
            service.create_plan(_plan(location_key="loc_foreign"))

    def test_create_with_own_location_accepted(self):
        site_repo = _FakeSiteRepo({"loc_beet_c": _location("loc_beet_c", TENANT)})
        service, _repo, _rs = self._service_with_site(site_repo)
        created = service.create_plan(_plan(location_key="loc_beet_c"))
        assert created.location_key == "loc_beet_c"

    def test_update_to_foreign_location_rejected(self):
        site_repo = _FakeSiteRepo(
            {
                "loc_beet_c": _location("loc_beet_c", TENANT),
                "loc_foreign": _location("loc_foreign", "tenant_other"),
            }
        )
        service, _repo, _rs = self._service_with_site(site_repo)
        created = service.create_plan(_plan(location_key="loc_beet_c"))
        with pytest.raises(NotFoundError):
            service.update_plan(created.key, {"location_key": "loc_foreign"}, tenant_key=TENANT)

    def test_generate_with_foreign_location_rejected(self):
        # Location becomes foreign after creation (e.g. re-parented); generation must
        # re-check before writing runs into another tenant's location.
        site_repo = _FakeSiteRepo({"loc_beet_c": _location("loc_beet_c", TENANT)})
        service, _repo, _rs = self._service_with_site(site_repo)
        created = service.create_plan(_plan(location_key="loc_beet_c"))
        site_repo._locations["loc_beet_c"] = _location("loc_beet_c", "tenant_other")
        with pytest.raises(NotFoundError):
            service.generate_runs(created.key, tenant_key=TENANT)
