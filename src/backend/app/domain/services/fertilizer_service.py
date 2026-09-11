from pydantic import ValidationError as PydanticValidationError

from app.common.exceptions import NotFoundError, ValidationError
from app.common.types import FertilizerKey, FertilizerStockKey
from app.domain.engines.area_dosing_engine import AreaDosingCalculator, AreaDosingResult
from app.domain.interfaces.fertilizer_repository import IFertilizerRepository
from app.domain.interfaces.site_repository import ISiteRepository
from app.domain.models.fertilizer import Fertilizer, FertilizerStock
from app.domain.services.location_ownership import resolve_owned_location


class FertilizerService:
    def __init__(self, repo: IFertilizerRepository, site_repo: ISiteRepository | None = None) -> None:
        self._repo = repo
        self._site_repo = site_repo
        self._area_calc = AreaDosingCalculator()

    # ── Fertilizer CRUD ──────────────────────────────────────────────

    def list_fertilizers(
        self,
        offset: int = 0,
        limit: int = 50,
        filters: dict | None = None,
        tenant_key: str = "",
    ) -> tuple[list[Fertilizer], int]:
        return self._repo.get_all(offset, limit, filters, tenant_key=tenant_key)

    def get_fertilizer(self, key: FertilizerKey, tenant_key: str = "") -> Fertilizer:
        fert = self._repo.get_or_raise(key)
        if tenant_key and fert.tenant_key not in ("", tenant_key):
            raise NotFoundError("Fertilizer", key)
        return fert

    def create_fertilizer(self, fertilizer: Fertilizer) -> Fertilizer:
        return self._repo.create(fertilizer)

    def update_fertilizer(self, key: FertilizerKey, data: dict) -> Fertilizer:
        existing = self.get_fertilizer(key)
        allowed_fields = {
            "product_name",
            "brand",
            "fertilizer_type",
            "is_organic",
            "tank_safe",
            "recommended_application",
            "npk_ratio",
            "ec_contribution_per_ml",
            "mixing_priority",
            "ph_effect",
            "bioavailability",
            "shelf_life_days",
            "storage_temp_min",
            "storage_temp_max",
            "application_rate_g_per_m2",
            "application_rate_l_per_m2",
            "dilution_ratio",
            "nutrient_release_speed",
            "notes",
        }
        merged = existing.model_dump()
        for field, value in data.items():
            if field in allowed_fields:
                merged[field] = value
        try:
            validated = Fertilizer.model_validate(merged)
        except PydanticValidationError as exc:
            raise ValidationError(
                message=str(exc.errors()[0]["msg"]),
                details=[
                    {"field": ".".join(str(loc) for loc in e["loc"]), "reason": e["msg"], "code": e["type"]}
                    for e in exc.errors()
                ],
            ) from exc
        return self._repo.update(key, validated)

    def delete_fertilizer(self, key: FertilizerKey) -> bool:
        self.get_fertilizer(key)  # ensure exists
        return self._repo.delete(key)

    # ── Stock CRUD ───────────────────────────────────────────────────

    def create_stock(
        self,
        fertilizer_key: FertilizerKey,
        stock: FertilizerStock,
        *,
        tenant_key: str,
    ) -> FertilizerStock:
        """Add a stock row, stamped with its owner (#1268).

        The tenant comes from the caller's context, never from the body — the
        #1000 rule. The product may be global (the seeded catalogue is), but the
        inventory of it is not: a batch number and a purchase price belong to
        one garden.
        """
        self.get_fertilizer(fertilizer_key, tenant_key)
        stock.fertilizer_key = fertilizer_key
        stock.tenant_key = tenant_key
        return self._repo.create_stock(stock)

    def get_stocks(self, fertilizer_key: FertilizerKey, *, tenant_key: str) -> list[FertilizerStock]:
        """This tenant's stocks of one product (#1268)."""
        self.get_fertilizer(fertilizer_key, tenant_key)
        return self._repo.get_stocks(fertilizer_key, tenant_key=tenant_key)

    #: Patchable through :meth:`update_stock`. ``fertilizer_key`` is deliberately
    #: absent: re-pointing a stock at another product is not an edit, it is a
    #: different record.
    STOCK_UPDATABLE_FIELDS = frozenset(
        {"current_volume_ml", "purchase_date", "expiry_date", "batch_number", "cost_per_liter"}
    )

    def update_stock(
        self,
        key: FertilizerStockKey,
        data: dict,
        *,
        fertilizer_key: FertilizerKey,
        tenant_key: str,
    ) -> FertilizerStock:
        """Patch one stock row, merged onto the stored document.

        Until #1265 this never read the stored row. It built a **fresh**
        ``FertilizerStock(fertilizer_key="temp", current_volume_ml=0)``, applied
        the patch fields to that, and handed it to ``_repo.update_stock`` —
        which is :meth:`BaseArangoRepository.update`, a full REPLACE. So a
        request changing only ``batch_number`` wrote ``fertilizer_key: "temp"``,
        detaching the stock from its product, and reset every unpatched field to
        its model default (``current_volume_ml`` to 0, ``purchase_date`` to
        ``None``). The comment "we need to find the stock first" stated the
        intent; the code never did it, because the repository had no read for a
        single stock. It has one now.

        ``fertilizer_key`` and ``tenant_key`` are keyword-only without defaults
        (#948/#1263): the route used to check the product named in the URL and
        then patch whatever stock key followed it, so the pairing is verified
        here where no caller can skip it.
        """
        existing = self._owned_stock_or_raise(key, tenant_key)
        if existing.fertilizer_key != fertilizer_key:
            # The same 404 a foreign row gets — naming product A while editing a
            # stock of product B must not be distinguishable from absence.
            raise NotFoundError("FertilizerStock", key)

        for field, value in data.items():
            if field in self.STOCK_UPDATABLE_FIELDS:
                setattr(existing, field, value)
        return self._repo.update_stock(key, existing)

    def delete_stock(self, key: FertilizerStockKey, *, fertilizer_key: FertilizerKey, tenant_key: str) -> bool:
        """Delete one stock row, ownership-checked like :meth:`update_stock`."""
        existing = self._owned_stock_or_raise(key, tenant_key)
        if existing.fertilizer_key != fertilizer_key:
            raise NotFoundError("FertilizerStock", key)
        return self._repo.delete_stock(key)

    def _owned_stock_or_raise(self, key: FertilizerStockKey, tenant_key: str) -> FertilizerStock:
        """Resolve a stock through its OWN tenant, then its product's visibility.

        #1265 could only check the PRODUCT's visibility, because
        ``FertilizerStock`` had no tenant — and for a global fertilizer that is
        "every tenant", so the check was explicitly not isolation. #1268 gave the
        stock an owner and that gap is closed: the stock's tenant is checked
        first, and the product check stays because a stock of a product this
        tenant cannot see is still not theirs to touch.

        An unattributable stock (``tenant_key == ""``, migration v0044) matches
        no real tenant and is therefore reachable by nobody in ``full`` mode.
        Fail-safe, and the same consequence v0043 accepted for substrate
        batches; in ``light`` mode the sole operator resolves to ``""`` and
        still reaches them.
        """
        stock = self._repo.get_stock_or_raise(key)
        if (stock.tenant_key or "") != tenant_key:
            # Anchored on the STOCK's own tenant since #1268. It used to hang on
            # the product's visibility, which for a global fertilizer is "every
            # tenant" — so this method's own docstring had to say it was not
            # isolation. It is now.
            raise NotFoundError("FertilizerStock", key)
        self.get_fertilizer(stock.fertilizer_key, tenant_key)
        return stock

    # ── Incompatibility ──────────────────────────────────────────────

    def add_incompatibility(
        self,
        key_a: FertilizerKey,
        key_b: FertilizerKey,
        reason: str,
        severity: str,
    ) -> dict:
        self.get_fertilizer(key_a)
        self.get_fertilizer(key_b)
        return self._repo.add_incompatibility(key_a, key_b, reason, severity)

    def get_incompatibilities(self, key: FertilizerKey) -> list[dict]:
        self.get_fertilizer(key)
        return self._repo.get_incompatibilities(key)

    def remove_incompatibility(self, key_a: FertilizerKey, key_b: FertilizerKey) -> bool:
        return self._repo.remove_incompatibility(key_a, key_b)

    # ── Reverse lookup ─────────────────────────────────────────────────

    def get_nutrient_plan_usage(self, key: FertilizerKey) -> list[dict]:
        self.get_fertilizer(key)  # ensure exists
        return self._repo.get_nutrient_plan_usage(key)

    # ── Area-based dosing (REQ-004 W-013, AP-11) ────────────────────────

    def calculate_area_dosage(
        self,
        fertilizer_keys: list[FertilizerKey],
        area_m2: float | None = None,
        location_key: str | None = None,
        demand_level: str | None = None,
        tenant_key: str = "",
    ) -> AreaDosingResult:
        """Compute per-area amounts for a set of fertilizers over a bed area.

        The area is taken from ``area_m2`` when provided (override); otherwise it
        is resolved from the location's ``area_m2`` (Location.area_m2). Exactly
        one source of area must yield a positive value.
        """
        resolved_area = self._resolve_area(area_m2, location_key, tenant_key)

        fertilizers = [self.get_fertilizer(key, tenant_key=tenant_key) for key in fertilizer_keys]

        try:
            return self._area_calc.calculate(fertilizers, resolved_area, demand_level)
        except ValueError as exc:
            raise ValidationError(message=str(exc)) from exc

    def _resolve_area(self, area_m2: float | None, location_key: str | None, tenant_key: str = "") -> float:
        """Resolve the application area; explicit ``area_m2`` overrides the location."""
        if area_m2 is not None:
            if area_m2 <= 0:
                raise ValidationError(message="area_m2 must be greater than 0.")
            return area_m2

        if location_key:
            if self._site_repo is None:
                raise ValidationError(message="Site repository not configured for location resolution.")
            # Tenant isolation (AP-8): a Location is a tenant resource, so a caller
            # must not resolve another tenant's bed area via its key.
            #
            # Anchored on the parent site (#1397). Written as
            # ``getattr(location, "tenant_key", None) != tenant_key`` this refused
            # **every** location including the caller's own, because the field is
            # empty on every row the write path produces — the #1352 direction, and
            # it made area-based organic dosing unusable through the location path.
            location = (
                resolve_owned_location(self._site_repo, location_key, tenant_key)
                if tenant_key
                else self._site_repo.get_location_or_raise(location_key)
            )
            if location.area_m2 <= 0:
                raise ValidationError(message="Location has no area (area_m2) configured.")
            return location.area_m2

        raise ValidationError(message="Either area_m2 or location_key must be provided.")
