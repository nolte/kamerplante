from datetime import date
from types import SimpleNamespace

import pytest

from app.common.enums import (
    FrostTolerance,
    HardinessRating,
    SiteType,
    SpringAction,
    WinterAction,
    WinterHardinessLight,
)
from app.common.exceptions import DuplicateError, NotFoundError, ValidationError, WinterPathViolationError
from app.domain.interfaces.overwintering_profile_repository import IOverwinteringProfileRepository
from app.domain.models.overwintering_profile import OverwinteringProfile
from app.domain.models.plant_instance import PlantInstance
from app.domain.models.site import Location, Site
from app.domain.services.overwintering_profile_service import OverwinteringProfileService


class FakeOverwinteringRepo(IOverwinteringProfileRepository):
    def __init__(self) -> None:
        self.store: dict[str, OverwinteringProfile] = {}
        self.edges: list[tuple] = []
        self._seq = 0

    def get_profile_by_key(self, key):
        return self.store.get(key)

    def get_profile_by_plant_key(self, plant_key):
        return next((p for p in self.store.values() if p.plant_key == plant_key), None)

    def get_profile_by_run_key(self, run_key):
        return next((p for p in self.store.values() if p.planting_run_key == run_key), None)

    def create_profile(self, profile):
        self._seq += 1
        key = f"ow{self._seq}"
        stored = profile.model_copy(update={"key": key})
        self.store[key] = stored
        return stored

    def update_profile(self, key, profile):
        stored = profile.model_copy(update={"key": key})
        self.store[key] = stored
        return stored

    def delete_profile(self, key):
        return self.store.pop(key, None) is not None

    def list_by_tenant(self, tenant_key, offset=0, limit=50):
        items = [p for p in self.store.values() if p.tenant_key == tenant_key]
        return items[offset : offset + limit], len(items)

    def create_subject_edge(self, profile_key, *, plant_key=None, planting_run_key=None):
        self.edges.append(("subject", profile_key, plant_key, planting_run_key))

    def create_winter_quarter_edge(self, profile_key, location_key):
        self.edges.append(("winter_quarter", profile_key, location_key))


TENANT = "tenant_anna"


@pytest.fixture
def service() -> OverwinteringProfileService:
    return OverwinteringProfileService(FakeOverwinteringRepo())


def _profile(**overrides) -> OverwinteringProfile:
    data = {
        "plant_key": "p1",
        "hardiness_rating": HardinessRating.HARDY,
        "winter_action": WinterAction.NONE,
        "winter_action_month": 10,
    }
    data.update(overrides)
    return OverwinteringProfile(**data)


class TestCreateD5:
    def test_valid_profile_created(self, service) -> None:
        created = service.create_profile(_profile(), TENANT)
        assert created.key
        assert created.tenant_key == TENANT

    def test_d5_contradiction_rejected(self, service) -> None:
        # path A rating (hardy) with a path B action (move_indoors) → 422
        bad = _profile(winter_action=WinterAction.MOVE_INDOORS)
        with pytest.raises(WinterPathViolationError):
            service.create_profile(bad, TENANT)

    def test_requires_exactly_one_subject(self, service) -> None:
        with pytest.raises(ValidationError):
            service.create_profile(_profile(plant_key=None, planting_run_key=None), TENANT)
        with pytest.raises(ValidationError):
            service.create_profile(_profile(plant_key="p1", planting_run_key="r1"), TENANT)

    def test_subject_edge_wired(self, service) -> None:
        created = service.create_profile(_profile(), TENANT)
        repo = service._repo
        assert ("subject", created.key, "p1", None) in repo.edges


class TestUpdateD5:
    def test_update_rejects_d5_contradiction(self, service) -> None:
        created = service.create_profile(_profile(), TENANT)
        with pytest.raises(WinterPathViolationError):
            service.update_profile(created.key, TENANT, {"winter_action": WinterAction.DIG_STORE})


class TestAutoGenerate:
    def test_red_species_relocated(self, service) -> None:
        profile = service.auto_generate_profile(TENANT, plant_key="p1", frost_sensitivity=FrostTolerance.SENSITIVE)
        assert profile.auto_generated is True
        assert profile.hardiness_rating == HardinessRating.FROST_FREE
        assert profile.winter_action == WinterAction.MOVE_INDOORS
        # B3 — a relocated container gets a consistent spring action + month.
        assert profile.spring_action == SpringAction.MOVE_OUTDOORS
        assert profile.spring_action_month is not None

    def test_green_species_in_situ(self, service) -> None:
        profile = service.auto_generate_profile(
            TENANT, plant_key="p1", frost_sensitivity=FrostTolerance.VERY_HARDY, species_zone="6a", site_zone="7a"
        )
        assert profile.hardiness_rating == HardinessRating.HARDY
        assert profile.winter_action == WinterAction.NONE
        # B3 — hardy, in-situ plants get no spring action nor a dangling month.
        assert profile.spring_action is None
        assert profile.spring_action_month is None

    def test_red_geophyte_dig_and_store(self, service) -> None:
        """B3 — a frost-tender geophyte on the red path is dug up and stored, not
        relocated as a container, and gets the replant spring action."""
        profile = service.auto_generate_profile(
            TENANT,
            plant_key="p1",
            frost_sensitivity=FrostTolerance.SENSITIVE,
            is_geophyte=True,
        )
        assert profile.hardiness_rating == HardinessRating.DIG_AND_STORE
        assert profile.winter_action == WinterAction.DIG_STORE
        assert profile.spring_action == SpringAction.REPLANT
        assert profile.spring_action_month is not None

    def test_bed_yellow_stays_path_a(self, service) -> None:
        """AC-26 baseline — a bed (non-container) yellow plant overwinters in-situ."""
        # MODERATE frost + no zone gap → yellow (path A) when in a bed.
        bed = service.auto_generate_profile(TENANT, plant_key="p1", frost_sensitivity=FrostTolerance.MODERATE)
        assert bed.winter_action == WinterAction.MULCH

    def test_container_flag_moves_indoors(self, service) -> None:
        """AC-26 — a potted (container) yellow plant is escalated to path B."""
        potted = service.auto_generate_profile(
            TENANT, plant_key="p1", frost_sensitivity=FrostTolerance.MODERATE, is_container=True
        )
        assert potted.hardiness_rating == HardinessRating.FROST_FREE
        assert potted.winter_action == WinterAction.MOVE_INDOORS

    def test_container_does_not_touch_green(self, service) -> None:
        """A fully hardy (green) plant is never escalated by the container flag."""
        profile = service.auto_generate_profile(
            TENANT,
            plant_key="p1",
            frost_sensitivity=FrostTolerance.VERY_HARDY,
            species_zone="6a",
            site_zone="7a",
            is_container=True,
        )
        assert profile.winter_action == WinterAction.NONE


class TestDuplicateSubject:
    def test_second_profile_for_same_plant_rejected(self, service) -> None:
        """B4 — a second profile for the same subject is a 409, not a 500."""
        service.create_profile(_profile(plant_key="p1"), TENANT)
        with pytest.raises(DuplicateError):
            service.create_profile(_profile(plant_key="p1"), TENANT)

    def test_edge_failure_rolls_back_document(self) -> None:
        """B4 — if the unique subject-edge insert fails (race), the freshly created
        profile document is deleted so no orphan remains."""

        class EdgeFailingRepo(FakeOverwinteringRepo):
            def create_subject_edge(self, profile_key, *, plant_key=None, planting_run_key=None):
                raise RuntimeError("unique constraint violated")

        repo = EdgeFailingRepo()
        service = OverwinteringProfileService(repo)
        with pytest.raises(DuplicateError):
            service.create_profile(_profile(plant_key="p1"), TENANT)
        assert repo.store == {}


class TestForeignKeyOwnership:
    def test_foreign_winter_quarter_rejected(self) -> None:
        """B5 — a winter quarter owned by another tenant is rejected (no edge)."""
        repo = FakeOverwinteringRepo()

        class SiteRepoStub:
            def get_location_by_key(self, key):
                return Location(_key=key, name="Foreign shed", area_m2=1.0, site_key="site_foreign")

            def get_site_by_key(self, key):
                return Site(_key=key, tenant_key="other_tenant", name="Woanders", site_type="indoor")

        service = OverwinteringProfileService(repo, site_repo=SiteRepoStub())
        profile = _profile(
            plant_key="p1",
            hardiness_rating=HardinessRating.FROST_FREE,
            winter_action=WinterAction.MOVE_INDOORS,
            winter_quarter_key="loc_foreign",
        )
        with pytest.raises(NotFoundError):
            service.create_profile(profile, TENANT)
        assert repo.store == {}
        assert repo.edges == []

    def test_foreign_plant_subject_rejected(self) -> None:
        """B5 — a plant subject owned by another tenant is rejected."""
        repo = FakeOverwinteringRepo()

        class PlantRepoStub:
            def get_by_key(self, key):
                return PlantInstance(
                    _key=key,
                    tenant_key="other_tenant",
                    instance_id="i1",
                    species_key="s1",
                    planted_on=date(2024, 1, 1),
                )

        service = OverwinteringProfileService(repo, plant_repo=PlantRepoStub())
        with pytest.raises(NotFoundError):
            service.create_profile(_profile(plant_key="p1"), TENANT)
        assert repo.store == {}


class _ForeignSiteRepoStub:
    """Every location resolves to another tenant's location."""

    def get_location_by_key(self, key):  # noqa: ANN001, ANN201
        return Location(_key=key, name="Foreign shed", area_m2=1.0, site_key="site_foreign")

    def get_site_by_key(self, key):  # noqa: ANN001, ANN201
        """A real site owned by someone else, not a missing one.

        "Absent" and "foreign" must both be refused, but only the second is what
        this stub is named for — and a stub that answers ``None`` would pass even
        against a guard that merely checks the site exists.
        """
        return Site(_key=key, tenant_key="other_tenant", name="Woanders", site_type="indoor")


class TestCreateSiteFrostGuard:
    """REQ-047 §3.4 — the manual create path only accepts a frost-exposed plant site."""

    def _service(self, *, plant, site) -> OverwinteringProfileService:
        return OverwinteringProfileService(
            FakeOverwinteringRepo(),
            plant_repo=_PlantRepoStub(plant),
            site_repo=_SiteRepoStub(site),
        )

    def test_indoor_site_rejected(self) -> None:
        site = SimpleNamespace(tenant_key=TENANT, type=SiteType.INDOOR)
        service = self._service(plant=_plant(), site=site)
        with pytest.raises(ValidationError):
            service.create_profile(_profile(plant_key="p1"), TENANT)

    def test_plant_without_site_rejected(self) -> None:
        service = self._service(plant=_plant(site_key=None), site=None)
        with pytest.raises(ValidationError):
            service.create_profile(_profile(plant_key="p1"), TENANT)

    def test_unresolvable_site_rejected(self) -> None:
        # A dangling site_key that the site repo cannot resolve is treated as
        # not-frost-exposed (fail-safe) rather than silently accepted.
        service = self._service(plant=_plant(), site=None)
        with pytest.raises(ValidationError):
            service.create_profile(_profile(plant_key="p1"), TENANT)

    def test_foreign_site_rejected(self) -> None:
        site = SimpleNamespace(tenant_key="other_tenant", type=SiteType.OUTDOOR)
        service = self._service(plant=_plant(), site=site)
        with pytest.raises(ValidationError):
            service.create_profile(_profile(plant_key="p1"), TENANT)

    def test_outdoor_site_accepted(self) -> None:
        site = SimpleNamespace(tenant_key=TENANT, type=SiteType.OUTDOOR)
        service = self._service(plant=_plant(), site=site)
        created = service.create_profile(_profile(plant_key="p1"), TENANT)
        assert created.key

    def test_balcony_site_accepted(self) -> None:
        site = SimpleNamespace(tenant_key=TENANT, type=SiteType.BALCONY)
        service = self._service(plant=_plant(), site=site)
        created = service.create_profile(_profile(plant_key="p1"), TENANT)
        assert created.key

    def test_greenhouse_site_accepted(self) -> None:
        site = SimpleNamespace(tenant_key=TENANT, type=SiteType.GREENHOUSE)
        service = self._service(plant=_plant(), site=site)
        created = service.create_profile(_profile(plant_key="p1"), TENANT)
        assert created.key

    def test_guard_skipped_without_repos(self, service) -> None:
        # No plant/site repos injected → the guard is skipped, so the legacy create
        # path (and its existing tests) keep working without a regression.
        created = service.create_profile(_profile(plant_key="p1"), TENANT)
        assert created.key

    def test_auto_generate_not_blocked_by_site_guard(self) -> None:
        # The automatic materialisation builds its document directly and never routes
        # through create_profile, so the frost-site guard cannot block it — even when
        # plant/site repos are present and the plant's site is indoor.
        service = self._service(
            plant=_plant(),
            site=SimpleNamespace(tenant_key=TENANT, type=SiteType.INDOOR),
        )
        profile = service.auto_generate_profile(TENANT, plant_key="p1", frost_sensitivity=FrostTolerance.SENSITIVE)
        assert profile.key
        assert profile.auto_generated is True


class TestOverrideForeignWinterQuarter:
    """B1 — a per-plant override/reset must never reference another tenant's location."""

    def _seed_red_profile(self, repo: FakeOverwinteringRepo, **overrides) -> None:
        data = {
            "plant_key": "p1",
            "hardiness_rating": HardinessRating.FROST_FREE,
            "winter_action": WinterAction.MOVE_INDOORS,
            "winter_action_month": 10,
            "tenant_key": TENANT,
        }
        data.update(overrides)
        repo.create_profile(OverwinteringProfile(**data))

    def test_override_with_foreign_winter_quarter_rejected(self) -> None:
        repo = FakeOverwinteringRepo()
        self._seed_red_profile(repo)
        service = OverwinteringProfileService(repo, site_repo=_ForeignSiteRepoStub())

        with pytest.raises(NotFoundError):
            service.override_plant_profile("p1", TENANT, {"winter_quarter_key": "loc_foreign"})

    def test_reset_does_not_retain_foreign_winter_quarter(self) -> None:
        """A foreign reference already stored on the profile is rejected on reset,
        never silently carried over."""
        repo = FakeOverwinteringRepo()
        self._seed_red_profile(repo, winter_quarter_key="loc_foreign")
        service = OverwinteringProfileService(repo, site_repo=_ForeignSiteRepoStub())

        with pytest.raises(NotFoundError):
            service.rematerialize_plant_profile("p1", TENANT, frost_sensitivity=FrostTolerance.SENSITIVE)


class _PlantRepoStub:
    def __init__(self, plant) -> None:
        self._plant = plant

    def get_by_key(self, key):  # noqa: ANN001, ANN201
        return self._plant


class _SpeciesRepoStub:
    def __init__(self, species) -> None:
        self._species = species

    def get_by_key(self, key):  # noqa: ANN001, ANN201
        return self._species


class _SiteRepoStub:
    def __init__(self, site) -> None:
        self._site = site

    def get_site_by_key(self, key):  # noqa: ANN001, ANN201
        return self._site


def _plant(**overrides) -> PlantInstance:
    data = {
        "_key": "p1",
        "tenant_key": TENANT,
        "instance_id": "i1",
        "species_key": "s1",
        "site_key": "site1",
        "planted_on": date(2024, 1, 1),
    }
    data.update(overrides)
    return PlantInstance(**data)


def _status_service(*, profile=None, plant=None, species=None, site=None) -> OverwinteringProfileService:
    repo = FakeOverwinteringRepo()
    if profile is not None:
        repo.create_profile(profile)
    return OverwinteringProfileService(
        repo,
        plant_repo=_PlantRepoStub(plant),
        species_repo=_SpeciesRepoStub(species),
        site_repo=_SiteRepoStub(site),
    )


class TestPlantHardinessStatus:
    """REQ-047 §4.3 — the three-way winter-hardiness status behind the empty state."""

    def test_existing_profile_reports_has_profile(self) -> None:
        profile = _profile(
            plant_key="p1",
            hardiness_rating=HardinessRating.NEEDS_PROTECTION,
            winter_action=WinterAction.FLEECE,
            tenant_key=TENANT,
        )
        service = _status_service(profile=profile)

        status = service.get_plant_hardiness_status("p1", TENANT)
        assert status.has_profile is True
        assert status.hardiness_light == WinterHardinessLight.YELLOW
        assert status.will_materialize is False
        # A materialised profile implies a frost-relevant site by construction.
        assert status.site_overwinterable is True

    def test_no_profile_yellow_will_materialize(self) -> None:
        # Fragaria-style: moderate frost sensitivity → half_hardy → yellow ampel.
        species = SimpleNamespace(frost_sensitivity=FrostTolerance.MODERATE, hardiness_zones=["7a"])
        site = SimpleNamespace(tenant_key=TENANT, climate_zone="7a", type=SiteType.OUTDOOR)
        service = _status_service(plant=_plant(), species=species, site=site)

        status = service.get_plant_hardiness_status("p1", TENANT)
        assert status.has_profile is False
        assert status.hardiness_light == WinterHardinessLight.YELLOW
        assert status.site_overwinterable is True
        assert status.will_materialize is True

    def test_no_profile_green_will_not_materialize(self) -> None:
        species = SimpleNamespace(frost_sensitivity=FrostTolerance.VERY_HARDY, hardiness_zones=["6a"])
        site = SimpleNamespace(tenant_key=TENANT, climate_zone="7a", type=SiteType.OUTDOOR)
        service = _status_service(plant=_plant(), species=species, site=site)

        status = service.get_plant_hardiness_status("p1", TENANT)
        assert status.has_profile is False
        assert status.hardiness_light == WinterHardinessLight.GREEN
        assert status.site_overwinterable is True
        assert status.will_materialize is False

    def test_indoor_site_never_materializes_even_when_yellow(self) -> None:
        # Same yellow-ampel species as the outdoor case, but on an indoor site: it is
        # never materialised, so `will_materialize` must stay False and the site is
        # flagged non-overwinterable (drives the FE indoor hint).
        species = SimpleNamespace(frost_sensitivity=FrostTolerance.MODERATE, hardiness_zones=["7a"])
        site = SimpleNamespace(tenant_key=TENANT, climate_zone="7a", type=SiteType.INDOOR)
        service = _status_service(plant=_plant(), species=species, site=site)

        status = service.get_plant_hardiness_status("p1", TENANT)
        assert status.has_profile is False
        assert status.hardiness_light == WinterHardinessLight.YELLOW
        assert status.site_overwinterable is False
        assert status.will_materialize is False

    def test_balcony_site_is_overwinterable_and_materializes_when_yellow(self) -> None:
        # REQ-047 §3.4 — a balcony is a frost-exposed outdoor location, so a yellow
        # plant there is overwinterable and will materialise just like outdoor.
        species = SimpleNamespace(frost_sensitivity=FrostTolerance.MODERATE, hardiness_zones=["7a"])
        site = SimpleNamespace(tenant_key=TENANT, climate_zone="7a", type=SiteType.BALCONY)
        service = _status_service(plant=_plant(), species=species, site=site)

        status = service.get_plant_hardiness_status("p1", TENANT)
        assert status.has_profile is False
        assert status.hardiness_light == WinterHardinessLight.YELLOW
        assert status.site_overwinterable is True
        assert status.will_materialize is True

    def test_unresolvable_species_keeps_site_eligibility(self) -> None:
        # Species unknown → ampel unknown, but the (outdoor) site is still resolved,
        # so the site-only eligibility flag survives from the single site read.
        site = SimpleNamespace(tenant_key=TENANT, climate_zone="7a", type=SiteType.OUTDOOR)
        service = _status_service(plant=_plant(), species=None, site=site)

        status = service.get_plant_hardiness_status("p1", TENANT)
        assert status.has_profile is False
        assert status.hardiness_light is None
        assert status.site_overwinterable is True
        assert status.will_materialize is False

    def test_foreign_site_is_unknown(self) -> None:
        species = SimpleNamespace(frost_sensitivity=FrostTolerance.MODERATE, hardiness_zones=["7a"])
        site = SimpleNamespace(tenant_key="other_tenant", climate_zone="7a", type=SiteType.OUTDOOR)
        service = _status_service(plant=_plant(), species=species, site=site)

        status = service.get_plant_hardiness_status("p1", TENANT)
        assert status.hardiness_light is None
        # A foreign site is never treated as eligible (fail-safe tenant guard).
        assert status.site_overwinterable is False
        assert status.will_materialize is False

    def test_foreign_profile_is_indistinguishable_from_no_profile(self) -> None:
        # SEC-001: a foreign-owned profile must NOT raise a 404 — that would be the
        # single case differing from the always-200 responses everywhere else and
        # would leak, cross-tenant, that this plant_key belongs to another tenant
        # and carries a profile. It must look exactly like "no profile".
        foreign = _profile(
            plant_key="p1",
            hardiness_rating=HardinessRating.NEEDS_PROTECTION,
            winter_action=WinterAction.FLEECE,
            tenant_key="other_tenant",
        )
        service = _status_service(profile=foreign, plant=None, species=None, site=None)

        status = service.get_plant_hardiness_status("p1", TENANT)
        assert status.has_profile is False
        assert status.hardiness_light is None
        assert status.site_overwinterable is False
        assert status.will_materialize is False

    def test_missing_repos_is_unknown(self) -> None:
        service = OverwinteringProfileService(FakeOverwinteringRepo())
        status = service.get_plant_hardiness_status("p1", TENANT)
        assert status.has_profile is False
        assert status.hardiness_light is None
        assert status.site_overwinterable is False
        assert status.will_materialize is False


class TestHardinessOverview:
    def test_aggregates_counts_and_red_list(self, service) -> None:
        service.create_profile(_profile(plant_key="p1"), TENANT)  # green
        service.create_profile(
            _profile(
                plant_key="p2", hardiness_rating=HardinessRating.NEEDS_PROTECTION, winter_action=WinterAction.FLEECE
            ),
            TENANT,
        )  # yellow
        service.create_profile(
            _profile(
                plant_key="p3", hardiness_rating=HardinessRating.FROST_FREE, winter_action=WinterAction.MOVE_INDOORS
            ),
            TENANT,
        )  # red
        service.create_profile(
            _profile(
                plant_key="p4", hardiness_rating=HardinessRating.DIG_AND_STORE, winter_action=WinterAction.DIG_STORE
            ),
            TENANT,
        )  # red

        overview = service.get_hardiness_overview(TENANT)
        assert overview.green == 1
        assert overview.yellow == 1
        assert overview.red == 2
        assert overview.total == 4
        assert {e.plant_key for e in overview.red_plants} == {"p3", "p4"}

    def test_overview_is_tenant_scoped(self, service) -> None:
        service.create_profile(_profile(plant_key="p1"), TENANT)
        service.create_profile(_profile(plant_key="p2"), "other_tenant")
        overview = service.get_hardiness_overview(TENANT)
        assert overview.total == 1

    @staticmethod
    def _seed_red_profile(repo: FakeOverwinteringRepo, *, plant_key: str, tenant_key: str = TENANT) -> None:
        """Insert a red (must-relocate) profile straight into the store.

        Bypasses ``create_profile`` (and its frost-exposed-site guard) so the test can
        target the overview enrichment in isolation.
        """
        key = f"ow_{plant_key}"
        repo.store[key] = _profile(
            plant_key=plant_key,
            hardiness_rating=HardinessRating.FROST_FREE,
            winter_action=WinterAction.MOVE_INDOORS,
        ).model_copy(update={"key": key, "tenant_key": tenant_key})

    def test_red_entries_enriched_with_plant_labels(self) -> None:
        """#631 — red entries carry a speaking name / species / location, not just keys."""
        repo = FakeOverwinteringRepo()

        class _PlantRepo:
            def get_by_key(self, key):  # noqa: ANN001, ANN201
                return PlantInstance(
                    _key=key,
                    tenant_key=TENANT,
                    instance_id="TOM-001",
                    species_key="s1",
                    location_key="loc1",
                    plant_name="Fensterbank-Tomate",
                    planted_on=date(2024, 1, 1),
                )

        class _SpeciesRepo:
            def get_by_key(self, key):  # noqa: ANN001, ANN201
                return SimpleNamespace(scientific_name="Solanum lycopersicum", common_names=["Tomate"])

        class _SiteRepo:
            """Stores what the write path stores: no ``tenant_key`` on the row.

            The tenant lives on the parent site (#1397). With ``tenant_key=TENANT``
            invented on the location, this test passed while the label condition
            in the service could never be true — it certified inert code.
            """

            def get_location_by_key(self, key):  # noqa: ANN001, ANN201
                return Location(_key=key, name="Balkon Süd", area_m2=1.0, site_key="site_own")

            def get_site_by_key(self, key):  # noqa: ANN001, ANN201
                return Site(_key=key, tenant_key=TENANT, name="Zuhause", site_type="indoor")

        self._seed_red_profile(repo, plant_key="p_red")
        service = OverwinteringProfileService(
            repo, plant_repo=_PlantRepo(), species_repo=_SpeciesRepo(), site_repo=_SiteRepo()
        )

        overview = service.get_hardiness_overview(TENANT)
        assert len(overview.red_plants) == 1
        entry = overview.red_plants[0]
        assert entry.plant_name == "Fensterbank-Tomate"
        assert entry.instance_id == "TOM-001"
        assert entry.species_common_name == "Tomate"
        assert entry.species_scientific_name == "Solanum lycopersicum"
        assert entry.location_name == "Balkon Süd"

    def test_foreign_tenant_labels_are_not_leaked(self) -> None:
        """SEC — enrichment never surfaces a plant/location owned by another tenant."""
        repo = FakeOverwinteringRepo()

        class _ForeignPlantRepo:
            def get_by_key(self, key):  # noqa: ANN001, ANN201
                return PlantInstance(
                    _key=key,
                    tenant_key="other_tenant",
                    instance_id="SECRET",
                    species_key="s1",
                    location_key="loc1",
                    plant_name="Foreign plant",
                    planted_on=date(2024, 1, 1),
                )

        self._seed_red_profile(repo, plant_key="p_red")
        service = OverwinteringProfileService(repo, plant_repo=_ForeignPlantRepo())

        overview = service.get_hardiness_overview(TENANT)
        entry = overview.red_plants[0]
        assert entry.plant_name is None
        assert entry.instance_id is None
        assert entry.location_name is None

    def test_overview_without_repos_keeps_keys(self) -> None:
        """No enrichment repos injected → entry still valid, labels just stay None."""
        repo = FakeOverwinteringRepo()
        self._seed_red_profile(repo, plant_key="p_red")
        service = OverwinteringProfileService(repo)

        entry = service.get_hardiness_overview(TENANT).red_plants[0]
        assert entry.plant_key == "p_red"
        assert entry.plant_name is None
        assert entry.species_scientific_name is None
