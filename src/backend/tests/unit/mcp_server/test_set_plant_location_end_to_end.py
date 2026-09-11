"""MCP `set_plant_location` against a real `SiteService` (#1352).

`test_tools.py` covers this tool with a `site_service` stub whose `get_location`
returns whatever it is handed. That proves the tool *calls* the verification —
the SEC-002 property it was written for — and it cannot see whether the
verification answers. It did not: `SiteService.get_location` compared the
caller's tenant against `Location.tenant_key`, which the write path never fills
(#1397), so every legitimate move was refused with 404.

This file closes that gap by wiring the real service over a repository double
shaped like the real repository. The distinction is the point of #1352: a stub
that stands in for the thing under suspicion cannot report on it.
"""

from types import SimpleNamespace

import pytest

from app.common.enums import TenantRole
from app.common.exceptions import NotFoundError
from app.domain.models.site import Location, Site, Slot
from app.domain.services.site_service import SiteService
from app.mcp_server.context import ToolContext
from app.mcp_server.principal import McpPrincipal, McpTenantMembership
from app.mcp_server.tools.plants import SetPlantLocation

TENANT = "home"


class FakeSiteRepo:
    """Rows as the application writes them: the tenant lives on the site only."""

    def __init__(self) -> None:
        self._sites = {
            "site_own": Site(_key="site_own", tenant_key=TENANT, name="Zuhause", site_type="indoor"),
            "site_foreign": Site(_key="site_foreign", tenant_key="other", name="Woanders", site_type="indoor"),
        }
        self._locations = {
            "loc_own": Location(_key="loc_own", name="Beet A", area_m2=1.0, site_key="site_own"),
            "loc_foreign": Location(_key="loc_foreign", name="Beet B", area_m2=1.0, site_key="site_foreign"),
        }
        self._slots = {"slot_own": Slot(_key="slot_own", location_key="loc_own", slot_id="LOCOWN_A1")}

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

    def get_site_or_raise(self, key):
        site = self._sites.get(key)
        if site is None:
            raise NotFoundError("Site", key)
        return site


def _ctx(plant_service) -> ToolContext:
    membership = McpTenantMembership(tenant_key=TENANT, tenant_slug=TENANT, tenant_name="Home", role=TenantRole.LEAD)
    principal = McpPrincipal(account_key="sa-1", display_name="bot", is_service_account=True, memberships=(membership,))
    return ToolContext(
        principal,
        membership,
        services={
            "plant_instance_service": plant_service,
            "site_service": SiteService(FakeSiteRepo()),
        },
    )


def _plant_service(written: dict):
    plant = SimpleNamespace(key="pl-1", site_key="site_own", location_key="loc_start", slot_key=None)

    def _update(key, p):
        written["location_key"] = p.location_key
        return p

    return SimpleNamespace(get_plant=lambda key, tenant_key: plant, update_plant=_update)


@pytest.mark.asyncio
async def test_a_move_to_the_tenants_own_location_succeeds():
    """The case #1352 measured as broken: 404 on every legitimate move."""
    written: dict = {}
    result = await SetPlantLocation().execute(
        _ctx(_plant_service(written)),
        SetPlantLocation.Input(plant_key="pl-1", location_key="loc_own"),
    )
    assert written["location_key"] == "loc_own"
    assert result.data["location_key"] == "loc_own"


@pytest.mark.asyncio
async def test_a_move_to_a_foreign_location_is_still_refused():
    """The control. The repair must not have opened what SEC-002 closed."""
    written: dict = {}
    with pytest.raises(NotFoundError):
        await SetPlantLocation().execute(
            _ctx(_plant_service(written)),
            SetPlantLocation.Input(plant_key="pl-1", location_key="loc_foreign"),
        )
    assert written == {}


@pytest.mark.asyncio
async def test_a_move_to_an_unknown_location_is_refused():
    written: dict = {}
    with pytest.raises(NotFoundError):
        await SetPlantLocation().execute(
            _ctx(_plant_service(written)),
            SetPlantLocation.Input(plant_key="pl-1", location_key="loc_nowhere"),
        )
    assert written == {}


@pytest.mark.asyncio
async def test_a_move_to_the_tenants_own_slot_succeeds():
    """Slots walk one hop further — slot → location → site (#1397)."""
    written: dict = {}
    result = await SetPlantLocation().execute(
        _ctx(_plant_service(written)),
        SetPlantLocation.Input(plant_key="pl-1", slot_key="slot_own"),
    )
    assert result.data["slot_key"] == "slot_own"
