"""Physical invariants of `substrates.yaml` that a JSON Schema cannot express (#1152).

The file declared no schema and shipped three physically impossible records: air
porosity plus water-holding capacity above 100 %, on the same pore space. Adding
`substrates.schema.yaml` pins structure, types and per-field ranges — but every
invariant that actually catches these defects is **cross-field**, and JSON Schema
has no arithmetic across properties. So the schema and this module are two halves
of one check, and a green schema run alone means less than it looks like.

Each rule below is asserted twice: once as a rule, against fixtures that sit on
its boundary, and once over the real seed file. The first is what makes the
boundary a decision rather than an accident of the data; the second is what makes
it bite.

Not covered here: the CEC plausibility band. Its *unit* is settled — the values
are per 100 cm³ of volume, the field is named ``cec_meq_per_100cm3`` and the mix
engine weights it by volume (#1152 §F) — but a per-type band still is not, and
writing one from the values present would only ratify them. The literature
figures in REQ-019 are mass-based (meq/100 g) and converting them needs each
source's own bulk density, which those sources mostly do not report; assembling
that table across fourteen substrate types is a data job, not an inference, and
#1175 deliberately leaves it rather than guessing a band. The one record that
fits neither reading is named in #1152 §F: sphagnum at CEC 8 and 30 g/L implies
267 meq/100 g, above its band, which is a second reason a band derived from this
data would be wrong.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.migrations.yaml_loader import load_yaml

#: Total porosity of even the lightest horticultural medium tops out around 95 %.
#: 100 is used as the invariant because it is the physically impossible line —
#: anything above it is wrong regardless of which medium is meant, so the rule
#: needs no per-type table to be correct.
_MAX_TOTAL_POROSITY = 100.0

#: Composition maps are volume fractions of one medium and must close.
_COMPOSITION_SUM = 1.0
_COMPOSITION_TOLERANCE = 0.01

#: Components that make a medium conductive. A record declaring one of these and
#: `ec_base_ms: 0.0` contradicts itself — and `ec_base_ms` is subtracted from the
#: target as EC-net in `calculate_mixing_protocol`, so the plant is dosed as if
#: the substrate contributed nothing.
_FERTILISER_COMPONENTS = frozenset(
    {"langzeitduenger", "organischer_duenger", "fledermausguano", "pre_mix", "wurmhumus"}
)

#: Amendments dosed by mass, not by volume. Lime and a trace-element blend go into
#: a growing medium at single-digit kg/m³ — well under one percent by volume — so a
#: normalised volume vector cannot carry them next to peat and perlite without
#: reading as ten percent lime (#1152 §C, #1175). They live in ``additives``, which
#: names them and asserts no quantity, because this file has no sourced dose rate
#: for any of them and its own header forbids inventing one.
#:
#: Deliberately only these three. ``wurmhumus``, ``organischer_duenger``,
#: ``fledermausguano``, ``pre_mix``, ``seetang``, ``knochenmehl``, ``blutmehl`` and
#: ``leonardit`` are bulk constituents at the percentages the records declare — a
#: wider set would have moved real volume out of the vector and made the
#: renormalisation below a rewrite rather than a rescale.
_ADDITIVE_COMPONENTS = frozenset({"kalk", "dolomit", "spurenelemente"})

#: Types that are not a medium at all. ``air_porosity_percent`` is a property of a
#: pore space, and a nutrient solution has none — the field does not apply rather
#: than evaluating to a number (#1152 §E).
_NON_SUBSTRATE_TYPES = frozenset({"hydro_solution", "none"})

#: Records that violate an invariant below and are **not** corrected here, because
#: correcting them needs a sourced horticultural value and this file's own header
#: says "do not invent or alter numeric values here". Registered rather than
#: skipped, in the shape ``SCHEMA_DEBT_CEILING`` and ``ALLOWED_DISCREPANCIES``
#: already use in this suite: a violation outside the register fails, and a
#: register entry that has *stopped* violating fails too, so the debt cannot
#: outlive the debt.
#:
#: Tracked in the follow-up issue split out of #1152.
#: Rule identifiers. Explicit constants rather than matching words in the failure
#: message: the first version of this register keyed relevance on ``"porosity" in
#: what`` while the message says "pore space", so the healed-check below never
#: fired and the register could never expire. Caught by healing an entry on a copy
#: of the seed file and observing green.
_RULE_POROSITY = "porosity"
_RULE_FERTILISER_EC = "fertiliser-ec"

_KNOWN_OPEN: dict[str, tuple[str, str]] = {
    # Empty since #1175 closed `Sphagnum-Moos (getrocknet)` with a citation (see the
    # record). The shape stays: the next unsourced violation registers here, with
    # its rule and the search that failed to source it, and leaves the moment it
    # is fixed.
}


def _substrates() -> list[dict[str, Any]]:
    return load_yaml("substrates.yaml")["substrates"]


def _label(entry: dict[str, Any]) -> str:
    return f"{entry.get('brand') or '-'} / {entry.get('name_de')}"


# ── the rules, on their own boundaries ───────────────────────────────────────


def _total_porosity(entry: dict[str, Any]) -> float:
    return float(entry.get("air_porosity_percent") or 0) + float(entry.get("water_holding_capacity_percent") or 0)


@pytest.mark.parametrize(
    ("air", "whc", "ok"),
    [(59.0, 40.0, True), (60.0, 40.0, True), (61.0, 40.0, False)],
    ids=["99", "100", "101"],
)
def test_the_porosity_rule_sits_where_it_is_meant_to(air: float, whc: float, ok: bool) -> None:
    """The boundary is pinned, not inferred from whatever the data happens to hold.

    Without this, a rule written as `< 100` or `<= 99` would look identical against
    today's file and disagree the first time a record lands exactly on 100.
    """
    entry = {"air_porosity_percent": air, "water_holding_capacity_percent": whc}

    assert (_total_porosity(entry) <= _MAX_TOTAL_POROSITY) is ok


def test_the_fertiliser_rule_needs_both_halves() -> None:
    """A fertilised medium with zero EC is the contradiction; either half alone is fine."""
    assert _declares_fertiliser({"composition": {"langzeitduenger": 0.05}})
    assert not _declares_fertiliser({"composition": {"perlit": 1.0}})


def _declares_fertiliser(entry: dict[str, Any]) -> bool:
    return bool(set(entry.get("composition") or {}) & _FERTILISER_COMPONENTS)


# ── the rules, over the real seed file ───────────────────────────────────────


def test_air_and_water_never_exceed_the_pore_space_they_share() -> None:
    """Both are volume percentages of the *same* pore space (#1152 §A).

    The three offenders were the two rockwool records (40 + 80, 35 + 85) and dried
    sphagnum (25 + 80). The other 26 entries sat between 53 % and 85 %, which is
    what rules out a definitional quirk of the field and leaves "three wrong
    values".

    **Sphagnum closed under #1175**, and the last register entry went with it —
    which the healed-check below enforced: with the values corrected and the entry
    still present the test failed with "must be removed from _KNOWN_OPEN". The pair
    is measured at the record's own bulk density (Kämäräinen et al. 2018, Mires and
    Peat 21(17): loosely packed 40 mm fibres at ≈30 g/dm³, ≈28 vol-% water at pF 1,
    total porosity 97.4–97.8 %). The old 80 was the saturation-and-drain reading
    (Müller & Glatzel 2021: 28.4 g/g at 0.03 g/cm³ = 85 vol-%), not the −10 hPa
    reading the field is defined in; the citations live in the record.
    """
    offenders = {
        e.get("name_de"): f"{e.get('air_porosity_percent')} + {e.get('water_holding_capacity_percent')}"
        for e in _substrates()
        if _total_porosity(e) > _MAX_TOTAL_POROSITY
    }

    _assert_only_known_open(offenders, _RULE_POROSITY, "air + water-holding exceeds the shared pore space")


def test_easily_available_water_is_a_subset_of_what_is_held() -> None:
    """Holds today; pinned so it stays true. A plant cannot extract more than is there."""
    violations = [
        f"{_label(e)}: eaw {e.get('easily_available_water_percent')} > whc {e.get('water_holding_capacity_percent')}"
        for e in _substrates()
        if e.get("easily_available_water_percent") is not None
        and e.get("water_holding_capacity_percent") is not None
        and float(e["easily_available_water_percent"]) > float(e["water_holding_capacity_percent"])
    ]

    assert not violations, "; ".join(violations)


def test_every_composition_closes() -> None:
    """Holds today; pinned because the maps are read as real proportions.

    That reading is what makes #1152 §C a defect rather than a labelling choice:
    if the vector sums to 1.0, a `kalk: 0.10` really is ten percent lime.
    """
    violations = [
        f"{_label(e)}: {sum((e.get('composition') or {}).values()):.3f}"
        for e in _substrates()
        # An *empty* composition is not a broken one: `Hydrokultur (kein Substrat)`
        # composes nothing because there is no substrate. The rule is "if a medium
        # names components, they close" — writing it as "every entry sums to 1.0"
        # would have forced a fake component onto the one honest record.
        if e.get("composition") and abs(sum(e["composition"].values()) - _COMPOSITION_SUM) > _COMPOSITION_TOLERANCE
    ]

    assert not violations, "composition fractions do not sum to 1.0: " + "; ".join(violations)


def test_a_fertilised_medium_declares_a_conductivity() -> None:
    """`Lechuza PON` declared 5 % slow-release fertiliser and `ec_base_ms: 0.0` (#1152 §B).

    Not a cosmetic contradiction: `ec_base_ms` is subtracted from the target as
    EC-net, so a plant in that medium is dosed as though the substrate contributed
    nothing at all.

    **Closed under #1175**, and the register entry went with it — which is what the
    healed-check below enforces. LECHUZA\'s own EU-FPR declaration lists the
    controlled-release fertiliser as an ingredient (so the component was the right
    half) and publishes "Elektrische Leitfähigkeit (EC): 5 mS/m" = 0.05 mS/cm (so
    the zero was the wrong half). The citation lives in the record.

    The rule stays, and stays over the whole file: it is the invariant, not a
    single record\'s ticket.
    """
    offenders = {
        e.get("name_de"): f"{sorted(set(e.get('composition') or {}) & _FERTILISER_COMPONENTS)} with ec_base_ms=0"
        for e in _substrates()
        if _declares_fertiliser(e) and float(e.get("ec_base_ms") or 0) == 0.0
    }

    _assert_only_known_open(offenders, _RULE_FERTILISER_EC, "a fertilised medium declares zero conductivity")


def test_every_entry_declaring_cec_also_declares_bulk_density() -> None:
    """Without bulk density the volume/mass conversion is not possible at all.

    Which is the precondition for #1152 §F's option 2 (rewrite the values) even
    being available — so it is worth holding true before the decision, not after.
    """
    missing = [
        _label(e)
        for e in _substrates()
        if e.get("cec_meq_per_100cm3") is not None and not e.get("bulk_density_g_per_l")
    ]

    assert not missing, "CEC declared without bulk_density_g_per_l: " + "; ".join(missing)


def _assert_only_known_open(offenders: dict[str, str], rule: str, what: str) -> None:
    """Fail on an unregistered violation, and on a register entry that has healed.

    Both directions matter. The first is the invariant. The second is what stops
    the register becoming a permanent exemption list: the moment a value is
    corrected its entry has to go, so "known open" cannot sit on data that is now
    fine. ``rule`` scopes the second check — a register keyed by record name has to
    know which invariant each entry answers to, or the porosity rule would report
    the EC entry as healed.
    """
    unregistered = {name: detail for name, detail in offenders.items() if name not in _KNOWN_OPEN}
    assert not unregistered, f"{what}: " + "; ".join(f"{n} ({d})" for n, d in sorted(unregistered.items()))

    healed = [name for name, (entry_rule, _) in _KNOWN_OPEN.items() if entry_rule == rule and name not in offenders]
    assert not healed, f"these no longer violate '{what}' and must be removed from _KNOWN_OPEN: {sorted(healed)}"


# ── additives are not bulk components (#1175 model fix 1) ────────────────────


def _is_amendment(entry: dict[str, Any]) -> bool:
    return bool(entry.get("is_amendment"))


def _additives_in_bulk(entry: dict[str, Any]) -> set[str]:
    return set(entry.get("composition") or {}) & _ADDITIVE_COMPONENTS


def test_the_additive_rule_exempts_an_amendment_and_only_an_amendment() -> None:
    """The rule is about *media*, and that scoping is the decision, not a loophole.

    A growing medium is mostly bulk, so a lime fraction inside its normalised
    vector is read as ten percent lime. An amendment **is** the concentrate — its
    dolomite really is a tenth of the product — so the same key means something
    else there. Pinned with fixtures so the exemption cannot later be widened by
    accident into "additive keys are fine anywhere".
    """
    medium = {"composition": {"torf": 0.9, "kalk": 0.1}}
    amendment = {"is_amendment": True, "composition": {"torf": 0.9, "dolomit": 0.1}}
    clean_medium = {"composition": {"torf": 0.7, "perlit": 0.3}}

    assert _additives_in_bulk(medium) and not _is_amendment(medium)
    assert _additives_in_bulk(amendment) and _is_amendment(amendment)
    assert not _additives_in_bulk(clean_medium)


def test_no_growing_medium_carries_an_additive_as_a_bulk_component() -> None:
    """One normalised vector cannot hold both bulk components and additives (#1152 §C).

    They differ by two orders of magnitude: peat and perlite are tens of percent
    of the volume, lime is kilograms per cubic metre. Because the vector closes to
    1.0 — pinned by ``test_every_composition_closes`` — a ``kalk: 0.10`` is a
    literal ten percent lime, which would put the medium far above the ``ph_base:
    6.2`` the same record declares.
    """
    offenders = {
        _label(e): sorted(_additives_in_bulk(e))
        for e in _substrates()
        if not _is_amendment(e) and _additives_in_bulk(e)
    }

    assert not offenders, "additives carried as bulk components: " + "; ".join(
        f"{n} ({', '.join(k)})" for n, k in sorted(offenders.items())
    )


# ── "not applicable" is absent, not a number (#1175 model fix 2) ─────────────


def test_a_non_substrate_declares_no_air_porosity() -> None:
    """``Hydrokultur`` carried ``air_porosity_percent: 100.0`` (#1152 §E).

    That is "not applicable" written as a number, and it does not stay in the
    record: the field is read by ``calculate_mix_properties``, by the substrate
    MCP summary and by the detail view, none of which can tell a measured 100 from
    a placeholder. The empty ``composition`` on the same record was already
    allowed to say "there is nothing here"; the porosity now says it the same way.
    """
    offenders = {
        _label(e): e.get("air_porosity_percent")
        for e in _substrates()
        if e.get("type") in _NON_SUBSTRATE_TYPES and e.get("air_porosity_percent") is not None
    }

    assert not offenders, "a non-substrate declares an air porosity: " + "; ".join(
        f"{n} ({v})" for n, v in sorted(offenders.items())
    )
