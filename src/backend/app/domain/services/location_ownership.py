"""One anchor for "does this location / slot belong to this tenant" (#1397).

``Location`` and ``Slot`` carry a ``tenant_key`` field that the write path never
fills. ``POST /t/{slug}/locations`` builds ``Location(**body.model_dump())`` and
``LocationCreate`` cannot carry a ``tenant_key`` — ``check_tenant_body_field``
(#1000) forbids it; ``create_slot`` and ``PUT /slots/{key}`` are the same shape.
So the field is ``""`` on every row an installation has ever written, and the
real anchor is the parent ``Site``, which is the only document in the chain that
carries the key.

Nine sites had read that empty field as if it meant something, in three
different directions — five refusing the tenant's **own** data, two holding a
condition that can never be true, and one projection quietly answering ``null``
where a name belongs. The count is why this is a module rather than a method on
one service: the services that need it hold an ``ISiteRepository`` but not each
other, and a sixth private copy is precisely what produced the nine.

**Why every refusal is a 404 naming the entity the caller asked for**, never the
site behind it: an absent location and a location under a foreign site must
answer identically, or the difference between the two messages is itself the
oracle the 404 exists to prevent.

**Why the resolvers raise.** A predicate returning ``True``/``False`` invites
each caller to decide what a ``False`` means, and that decision is exactly where
the nine sites diverged. The resolvers raise, and hand back the document so the
caller does not read it twice.

:func:`find_owned_location` is the deliberate exception, for the two callers
whose answer is genuinely not a refusal: a label that is shown or omitted, and a
system task that iterates every tenant and skips what is not the subject's. It
returns the document rather than a boolean, so neither has to read the row a
second time to use it — which is what a plain predicate would have cost them.
"""

from typing import Protocol

from app.common.exceptions import NotFoundError
from app.domain.models.site import Location, Site, Slot


class SiteAnchorSource(Protocol):
    """The three reads an ownership walk needs.

    Narrower than ``ISiteRepository`` on purpose: this states what the anchor
    depends on, so a collaborator that satisfies it — a test double included —
    cannot drift into satisfying something larger by accident.
    """

    def get_site_by_key(self, key: str) -> Site | None: ...

    def get_location_by_key(self, key: str) -> Location | None: ...

    def get_slot_by_key(self, key: str) -> Slot | None: ...


def require_owned_site(
    source: SiteAnchorSource,
    site_key: str,
    tenant_key: str,
    entity_name: str,
    entity_key: str,
) -> Site:
    """Resolve ``site_key`` and require it to belong to ``tenant_key``.

    ``entity_name`` / ``entity_key`` name the object the **caller** asked about,
    which is usually the location or slot whose site this is — see the module
    docstring for why the message must not name the site.
    """
    site = source.get_site_by_key(site_key) if site_key else None
    if site is None or site.tenant_key != tenant_key:
        raise NotFoundError(entity_name, entity_key)
    return site


def resolve_owned_location(
    source: SiteAnchorSource,
    location_key: str,
    tenant_key: str,
) -> Location:
    """The location behind ``location_key``, or ``NotFoundError``.

    Refuses when the location does not exist, when it names no site, and when
    that site belongs to another tenant — all three with the same answer.
    """
    location = source.get_location_by_key(location_key) if location_key else None
    if location is None:
        raise NotFoundError("Location", location_key)
    require_owned_site(source, location.site_key, tenant_key, "Location", location_key)
    return location


def resolve_owned_slot(
    source: SiteAnchorSource,
    slot_key: str,
    tenant_key: str,
) -> tuple[Slot, Location]:
    """The slot behind ``slot_key`` and its location, or ``NotFoundError``.

    Two hops rather than one: a slot's tenant is its location's site's tenant.
    The location comes back because every caller so far needs it — to compare
    against a supplied ``location_key``, or to derive one.
    """
    slot = source.get_slot_by_key(slot_key) if slot_key else None
    if slot is None:
        raise NotFoundError("Slot", slot_key)
    location = source.get_location_by_key(slot.location_key) if slot.location_key else None
    if location is None:
        raise NotFoundError("Slot", slot_key)
    require_owned_site(source, location.site_key, tenant_key, "Slot", slot_key)
    return slot, location


def find_owned_location(
    source: SiteAnchorSource,
    location_key: str,
    tenant_key: str,
) -> Location | None:
    """The location if it belongs to ``tenant_key``, else ``None`` — without raising.

    For a caller whose "no" is not a refusal. Absent, site-less and foreign all
    answer ``None``, because none of them is a location this tenant may be told
    about; a caller that needs to tell those apart wants
    :func:`resolve_owned_location` instead.
    """
    try:
        return resolve_owned_location(source, location_key, tenant_key)
    except NotFoundError:
        return None
