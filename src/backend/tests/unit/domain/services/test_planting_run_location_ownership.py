"""A planting run may not point at another tenant's location (#1372).

`PlantingRunService.create_run` and `update_run` took `location_key` from the
request body and never resolved it. Everything downstream then read that location
**unscoped**, because a `Location` carries no usable `tenant_key` (#1397):

* `create_plants` asks `get_existing_ids_at_location` and `_get_available_slots`
  for the foreign location's plants and slots;
* it writes each batch instance with `self._plant_repo.create`, bypassing
  `PlantInstanceService.create_plant` and therefore the reference resolution
  #1349 added;
* `ArangoPlantInstanceRepository.create` then writes a `PLACED_IN` edge to a
  foreign slot, and the service sets `currently_occupied` on that slot — a write
  into another tenant's document.

The rotation and companion guards do not catch it. They read the slot's
neighbourhood tenant-scoped, so a foreign slot yields no findings and **passes**.
The reference has to be refused before it is interpreted.

Asserted at the writes, not only at the status of the call: a refusal that
happened after `update_slot` would satisfy a `pytest.raises` and still have
occupied the other tenant's slot.
"""

import pytest

from app.common.enums import PlantingRunStatus, PlantingRunType
from app.common.exceptions import NotFoundError
from app.domain.models.planting_run import PlantingRun, PlantingRunEntry
from app.domain.models.site import Location, Site, Slot
from app.domain.services.planting_run_service import PlantingRunService

OWN = "tenant_own"
FOREIGN = "tenant_foreign"


class FakeSiteRepo:
    """Sites, locations and slots as the write path stores them.

    Locations and slots carry **no** `tenant_key` — that is the whole point of
    #1397 — so the only way to tell them apart is the site they hang under.
    `update_slot` and `get_slots_by_location` record their calls, because the
    acceptance criterion is that neither reaches the foreign location.
    """

    def __init__(self) -> None:
        self.sites = {
            "site_own": Site(_key="site_own", tenant_key=OWN, name="Zuhause", type="indoor"),
            "site_foreign": Site(_key="site_foreign", tenant_key=FOREIGN, name="Woanders", type="indoor"),
        }
        self.locations = {
            "loc_own": Location(_key="loc_own", name="Beet A", area_m2=1.0, site_key="site_own"),
            "loc_foreign": Location(_key="loc_foreign", name="Beet B", area_m2=1.0, site_key="site_foreign"),
        }
        self.slots = {
            "loc_own": [Slot(_key="slot_own", location_key="loc_own", slot_id="LOCOWN_A1")],
            "loc_foreign": [Slot(_key="slot_foreign", location_key="loc_foreign", slot_id="LOCFOREIGN_A1")],
        }
        self.slot_reads: list[str] = []
        self.slot_writes: list[str] = []

    def get_site_by_key(self, key):
        return self.sites.get(key)

    def get_location_by_key(self, key):
        return self.locations.get(key)

    def get_slot_by_key(self, key):
        for slots in self.slots.values():
            for slot in slots:
                if slot.key == key:
                    return slot
        return None

    def get_slots_by_location(self, location_key):
        self.slot_reads.append(location_key)
        return list(self.slots.get(location_key, []))

    def update_slot(self, key, slot):
        self.slot_writes.append(key)
        return slot


class FakeRunRepo:
    def __init__(self) -> None:
        self.store: dict[str, PlantingRun] = {}
        self.entries: list[PlantingRunEntry] = []
        self._seq = 0

    def create(self, run: PlantingRun) -> PlantingRun:
        self._seq += 1
        key = f"run{self._seq}"
        stored = run.model_copy(update={"key": key})
        self.store[key] = stored
        return stored

    def create_entry(self, entry: PlantingRunEntry) -> PlantingRunEntry:
        self.entries.append(entry)
        return entry

    def get_by_key(self, key):
        return self.store.get(key)

    def get_or_raise(self, key):
        run = self.store.get(key)
        if run is None:
            raise NotFoundError("PlantingRun", key)
        return run

    def update(self, key, run):
        self.store[key] = run
        return run

    def get_entries(self, run_key):
        return [e for e in self.entries if e.run_key == run_key]


def _service(site_repo: FakeSiteRepo, run_repo: FakeRunRepo) -> PlantingRunService:
    from unittest.mock import MagicMock

    engine = MagicMock()
    engine.validate_run_type_constraints.return_value = None
    return PlantingRunService(
        run_repo,
        MagicMock(),
        engine=engine,
        site_repo=site_repo,
    )


def _run(location_key: str | None, tenant_key: str = OWN) -> PlantingRun:
    return PlantingRun(
        tenant_key=tenant_key,
        name="Tomaten Frühjahr",
        run_type=PlantingRunType.MONOCULTURE,
        location_key=location_key,
    )


@pytest.fixture
def site_repo() -> FakeSiteRepo:
    return FakeSiteRepo()


@pytest.fixture
def run_repo() -> FakeRunRepo:
    return FakeRunRepo()


class TestCreateRun:
    def test_a_run_at_the_tenants_own_location_is_created(self, site_repo, run_repo):
        """The control. Without it a guard that refuses everything passes below.

        This is not hypothetical here: refusing every location is exactly what
        five sibling sites did (#1352, #1397), for the same reason.
        """
        created = _service(site_repo, run_repo).create_run(_run("loc_own"))
        assert created.key in run_repo.store
        assert created.location_key == "loc_own"

    def test_a_run_at_a_foreign_location_is_refused(self, site_repo, run_repo):
        with pytest.raises(NotFoundError):
            _service(site_repo, run_repo).create_run(_run("loc_foreign"))

    def test_the_refused_run_is_not_written(self, site_repo, run_repo):
        """A refusal after the insert would still leave the row behind."""
        with pytest.raises(NotFoundError):
            _service(site_repo, run_repo).create_run(_run("loc_foreign"))
        assert run_repo.store == {}

    def test_the_refusal_reaches_no_slot_of_the_foreign_location(self, site_repo, run_repo):
        """Neither read nor write — the criterion #1372 states."""
        with pytest.raises(NotFoundError):
            _service(site_repo, run_repo).create_run(_run("loc_foreign"))
        assert site_repo.slot_reads == []
        assert site_repo.slot_writes == []

    def test_an_unknown_location_is_refused_like_a_foreign_one(self, site_repo, run_repo):
        """Same answer, so the message is not an existence oracle."""
        with pytest.raises(NotFoundError):
            _service(site_repo, run_repo).create_run(_run("loc_nowhere"))

    def test_a_run_without_a_location_is_untouched(self, site_repo, run_repo):
        """`location_key` is optional; a run may be planned before it is placed."""
        created = _service(site_repo, run_repo).create_run(_run(""))
        assert created.key in run_repo.store

    def test_a_tenantless_run_is_skipped(self, site_repo, run_repo):
        """Seeds, migrations and light mode have no tenant to anchor against.

        Matches the `if not plant.tenant_key` gate on the single-plant path.
        """
        created = _service(site_repo, run_repo).create_run(_run("loc_foreign", tenant_key=""))
        assert created.key in run_repo.store


class TestCloneConfig:
    """`_apply_clone_config` writes `location_key` too, and it used to write it after the check.

    The guard originally ran before the clone block. `_require_owned_location`
    returns early for a run with no location, so a request with `location_key:
    null` and a `clone_from_run_key` passed it trivially — and then the clone
    copied `template.location_key` onto the run, unresolved.

    That is reachable rather than theoretical: nothing verified
    `PlantingRun.location_key` before #1372, which is the premise of this change,
    so a run carrying a foreign key can exist. Cloning it launders the key into new
    runs, past the guard this change adds.
    """

    def _template(self, site_repo, run_repo, location_key: str) -> str:
        """A stored run pointing at `location_key`, written past the service.

        Deliberately not through `create_run`: that is the path under test, and it
        now refuses a foreign location. A row predating the guard is what this
        models, so it is inserted the way the repository holds it.
        """
        created = run_repo.create(_run("loc_own"))
        run_repo.store[created.key] = created.model_copy(update={"location_key": location_key})
        return created.key

    def test_a_clone_of_a_run_at_a_foreign_location_is_refused(self, site_repo, run_repo):
        template_key = self._template(site_repo, run_repo, "loc_foreign")
        clone = _run(None)
        clone.clone_from_run_key = template_key

        with pytest.raises(NotFoundError):
            _service(site_repo, run_repo).create_run(clone)

    def test_the_refused_clone_reaches_no_slot_of_the_foreign_location(self, site_repo, run_repo):
        template_key = self._template(site_repo, run_repo, "loc_foreign")
        clone = _run(None)
        clone.clone_from_run_key = template_key

        with pytest.raises(NotFoundError):
            _service(site_repo, run_repo).create_run(clone)
        assert site_repo.slot_reads == []
        assert site_repo.slot_writes == []

    def test_a_clone_of_a_run_at_the_tenants_own_location_is_created(self, site_repo, run_repo):
        """The control: the guard must not refuse the ordinary clone."""
        template_key = self._template(site_repo, run_repo, "loc_own")
        clone = _run(None)
        clone.clone_from_run_key = template_key

        created = _service(site_repo, run_repo).create_run(clone)
        assert created.location_key == "loc_own"


class TestUpdateRun:
    def _planned_run(self, site_repo, run_repo) -> str:
        created = _service(site_repo, run_repo).create_run(_run("loc_own"))
        return created.key

    def test_repointing_to_the_tenants_own_location_is_allowed(self, site_repo, run_repo):
        service = _service(site_repo, run_repo)
        key = self._planned_run(site_repo, run_repo)
        updated = service.update_run(key, {"location_key": "loc_own"})
        assert updated.location_key == "loc_own"

    def test_repointing_to_a_foreign_location_is_refused(self, site_repo, run_repo):
        service = _service(site_repo, run_repo)
        key = self._planned_run(site_repo, run_repo)
        with pytest.raises(NotFoundError):
            service.update_run(key, {"location_key": "loc_foreign"})

    def test_the_refused_update_does_not_persist_the_foreign_key(self, site_repo, run_repo):
        service = _service(site_repo, run_repo)
        key = self._planned_run(site_repo, run_repo)
        with pytest.raises(NotFoundError):
            service.update_run(key, {"location_key": "loc_foreign"})
        assert run_repo.store[key].location_key == "loc_own"

    def test_the_refused_update_never_reaches_slot_reassignment(self, site_repo, run_repo):
        """`_reassign_plant_slots` frees old slots and occupies new ones.

        It runs after the write, so a guard placed after the write would already
        have persisted the foreign key by the time it refused — and on an active
        run it would also have written into the other tenant's slots.
        """
        service = _service(site_repo, run_repo)
        key = self._planned_run(site_repo, run_repo)
        run_repo.store[key] = run_repo.store[key].model_copy(update={"status": PlantingRunStatus.ACTIVE})
        with pytest.raises(NotFoundError):
            service.update_run(key, {"location_key": "loc_foreign"})
        assert site_repo.slot_writes == []
