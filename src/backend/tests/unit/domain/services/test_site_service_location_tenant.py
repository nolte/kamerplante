"""`SiteService.get_location` / `get_slot` find the tenant's own rows (#1352).

Both compared the caller's tenant against `Location.tenant_key` / `Slot.tenant_key`,
which the write path never fills (#1397) — so with a tenant key supplied they
refused **every** location and slot, the caller's own included. The
over-rejecting direction: a guard that looks correct, passes every negative test
written for it, and is harmful.

Three callers reach these two methods with a tenant key, and MCP `set_plant_location`
is the one #1352 measured: it answered 404 to every legitimate move. Its own unit
test could not see that, because it stubs `site_service.get_location` and asserts
the call was made rather than that it succeeds. This file drives the real service
over a repository double shaped like the real one.
"""

import pytest

from app.common.exceptions import NotFoundError
from app.domain.models.site import Location, Site, Slot
from app.domain.services.site_service import SiteService

OWN = "tenant_own"
FOREIGN = "tenant_foreign"


class FakeSiteRepo:
    """Rows as `create_site` / `create_location` / `create_slot` write them.

    The locations and slots carry no `tenant_key`: `LocationCreate` and
    `SlotCreate` may not declare one (#1000), and both create paths do
    `Model(**body.model_dump())`. A double that invented the field would let the
    old, broken comparison pass — which is what the suites covering the sibling
    services did for months.
    """

    def __init__(self) -> None:
        self._sites = {
            "site_own": Site(_key="site_own", tenant_key=OWN, name="Zuhause", type="indoor"),
            "site_foreign": Site(_key="site_foreign", tenant_key=FOREIGN, name="Woanders", type="indoor"),
        }
        self._locations = {
            "loc_own": Location(_key="loc_own", name="Beet A", area_m2=1.0, site_key="site_own"),
            "loc_foreign": Location(_key="loc_foreign", name="Beet B", area_m2=1.0, site_key="site_foreign"),
        }
        self._slots = {
            "slot_own": Slot(_key="slot_own", location_key="loc_own", slot_id="LOCOWN_A1"),
            "slot_foreign": Slot(_key="slot_foreign", location_key="loc_foreign", slot_id="LOCFOREIGN_A1"),
        }

    def get_site_by_key(self, key):
        return self._sites.get(key)

    def get_location_by_key(self, key):
        return self._locations.get(key)

    def get_slot_by_key(self, key):
        return self._slots.get(key)

    def get_location_or_raise(self, key):
        location = self._locations.get(key)
        if location is None:
            raise NotFoundError("Location", key)
        return location

    def get_slot_or_raise(self, key):
        slot = self._slots.get(key)
        if slot is None:
            raise NotFoundError("Slot", key)
        return slot


@pytest.fixture
def service() -> SiteService:
    return SiteService(FakeSiteRepo())


class TestGetLocation:
    def test_the_tenants_own_location_is_found(self, service):
        """Red before #1352 was repaired. The other three below were green throughout."""
        assert service.get_location("loc_own", tenant_key=OWN).key == "loc_own"

    def test_a_foreign_location_is_refused(self, service):
        with pytest.raises(NotFoundError):
            service.get_location("loc_foreign", tenant_key=OWN)

    def test_an_absent_location_is_refused(self, service):
        with pytest.raises(NotFoundError):
            service.get_location("loc_nowhere", tenant_key=OWN)

    def test_without_a_tenant_key_the_lookup_is_unscoped(self, service):
        """Unchanged: internal callers (seeds, migrations, light mode) pass none."""
        assert service.get_location("loc_foreign").key == "loc_foreign"


class TestGetSlot:
    def test_the_tenants_own_slot_is_found(self, service):
        assert service.get_slot("slot_own", tenant_key=OWN).key == "slot_own"

    def test_a_slot_in_a_foreign_location_is_refused(self, service):
        with pytest.raises(NotFoundError):
            service.get_slot("slot_foreign", tenant_key=OWN)

    def test_an_absent_slot_is_refused(self, service):
        with pytest.raises(NotFoundError):
            service.get_slot("slot_nowhere", tenant_key=OWN)

    def test_without_a_tenant_key_the_lookup_is_unscoped(self, service):
        assert service.get_slot("slot_foreign").key == "slot_foreign"
