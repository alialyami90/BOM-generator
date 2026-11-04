"""Every override a build applied, in one list (ADR 0040, plan M77).

The engine computes each value and the file may replace it; this module walks the
inputs and the build result and names each replacement with the automatic value it
stands in for. An override that weakens a check is *risky* and needs the one-line
reason stored beside it (``options.override_reasons``, ``spares_list.reasons``).
"""

from collections.abc import Callable
from dataclasses import dataclass

from bomgen.engine.errors import EngineError
from bomgen.engine.spares import spares
from bomgen.engine.units import lookup
from bomgen.io.loader import LoadedSubstation
from bomgen.models.bom import BuildResult
from bomgen.models.panel import Panel, Ventilation
from bomgen.models.report import CheckItem, CheckStatus
from bomgen.models.substation import DeviceMove, OverrideNote, PairMove


@dataclass(frozen=True)
class Override:
    """One value the file replaced: what the engine gives, what the file says."""

    subject: str
    automatic: str
    override: str
    panel_id: str | None = None
    risky: bool = False  # it weakens a check, so it needs a reason
    reason: str | None = None
    field: str | None = None  # where Checks' "Go to the field" leads (substation.yaml)


def overrides(loaded: LoadedSubstation, result: BuildResult) -> list[Override]:
    """Every override, panel by panel, then the Parts rows, the layout, the spares list
    and the switch counts."""
    found: list[Override] = []
    for panel in loaded.panels:
        found += _panel_overrides(loaded, panel, result)
    found += _part_overrides(loaded)
    found += _layout_overrides(loaded)
    found += _spares_overrides(loaded, result)
    found += _switch_counts(loaded)
    return found


def override_checks(loaded: LoadedSubstation, result: BuildResult) -> list[CheckItem]:
    """The *Overrides* group of the check report: a risky override without a reason warns."""
    items = []
    for o in overrides(loaded, result):
        message = f"{o.override} instead of the automatic {o.automatic}"
        if o.reason:
            message += f": {o.reason}"
        elif o.risky:
            message += "; below the automatic value: give a reason"
        values: dict[str, int | float | str] = {"automatic": o.automatic, "override": o.override}
        if o.reason:
            values["reason"] = o.reason
        if o.field:
            values["field"] = o.field
        items.append(
            CheckItem(
                check="override",
                status=CheckStatus.WARN if o.risky and not o.reason else CheckStatus.PASS,
                panel_id=o.panel_id,
                subject=o.subject,
                message=message,
                values=values,
            )
        )
    return items


def risky_notes(loaded: LoadedSubstation, result: BuildResult) -> list[OverrideNote]:
    """The risky overrides as an issue records them (ADR 0040)."""
    return [
        OverrideNote(
            panel_id=o.panel_id,
            subject=o.subject,
            automatic=o.automatic,
            override=o.override,
            reason=o.reason,
        )
        for o in overrides(loaded, result)
        if o.risky
    ]


def _panel_overrides(loaded: LoadedSubstation, panel: Panel, result: BuildResult) -> list[Override]:
    options = panel.options
    reasons = options.override_reasons
    where = _option_field(loaded, panel)
    found: list[Override] = []

    def rating(subject: str, key: str, own: int | None, rule_a: int) -> None:
        if own is None or not rule_a:
            return
        found.append(
            Override(
                subject=subject,
                automatic=f"{rule_a} A",
                override=f"{own} A",
                panel_id=panel.id,
                risky=own < rule_a,
                reason=reasons.get(subject),
                field=where(key),
            )
        )

    main = next((m for m in result.mains if m.panel_id == panel.id), None)
    if main is not None:
        rating("main_mcb", "main_mcb_override_a", options.main_mcb_override_a, main.rule_rating_a)
    spare = next((s for s in result.spares if s.panel_id == panel.id), None)
    if spare is not None:
        rating("ac_spare", "ac_spare_rating_a", options.ac_spare_rating_a, spare.ac_rule_a)
        rating("dc_spare", "dc_spare_rating_a", options.dc_spare_rating_a, spare.dc_rule_a)
    seen: set[str] = set()
    for branch in result.housekeeping:
        if branch.panel_id != panel.id or branch.key in seen:
            continue
        seen.add(branch.key)
        own = options.housekeeping.branch_ratings.get(branch.key)
        rating(
            f"housekeeping.{branch.key}",
            f"housekeeping.branch_ratings.{branch.key}",
            own,
            branch.rule_rating_a,
        )
    strips = next((s.strips for s in result.strips if s.panel_id == panel.id), ())
    for strip in strips:
        subject = f"terminals.{strip.code}"
        if strip.override is not None:
            found.append(
                Override(
                    subject=subject,
                    automatic=str(strip.auto_qty),
                    override=str(strip.override),
                    panel_id=panel.id,
                    risky=strip.override < strip.auto_qty,
                    reason=reasons.get(subject),
                    field=where(f"terminal_overrides.{strip.code}"),
                )
            )
        if strip.block_override is not None:
            found.append(
                Override(
                    subject=f"{subject}.block",
                    automatic=strip.block,
                    override=strip.block_override,
                    panel_id=panel.id,
                    field=where(f"terminal_block_overrides.{strip.code}"),
                )
            )
    if options.ventilation is not Ventilation.AUTO and result.heat is not None:
        cabinet = next((c for c in result.heat.cabinets if c.panel_id == panel.id), None)
        if cabinet is not None:
            automatic = Ventilation.NATURAL if cabinet.natural.passes else Ventilation.FORCED
            found.append(
                Override(
                    subject="ventilation",
                    automatic=_VENTILATION[automatic],
                    override=_VENTILATION[options.ventilation],
                    panel_id=panel.id,
                    risky=options.ventilation is Ventilation.NATURAL and not cabinet.natural.passes,
                    reason=reasons.get("ventilation"),
                    field=where("ventilation"),
                )
            )
    return found


_VENTILATION = {Ventilation.NATURAL: "filters", Ventilation.FORCED: "fans"}


def _option_field(loaded: LoadedSubstation, panel: Panel) -> Callable[[str], str | None]:
    """Where a generated panel's option lives in substation.yaml; a hand-written panel's
    file is not reachable from Checks, so its overrides carry no field."""
    generated = loaded.substation.generated_panels
    if not panel.generated or generated is None:
        return lambda _key: None
    number = next((n for n in range(1, 1000) if generated.id.format(n=n) == panel.id), None)
    own = generated.options_by_panel.get(number, {}) if number is not None else {}

    def where(key: str) -> str | None:
        head = key.split(".")[0]
        if number is not None and head in own:
            return f"generated_panels.options_by_panel[{number}].{key}"
        return f"generated_panels.options.{key}"

    return where


def _part_overrides(loaded: LoadedSubstation) -> list[Override]:
    """Part values and SFP counts the Parts rows replace (ADR 0024, plan M49)."""
    found: list[Override] = []
    spare_per_l1 = loaded.spares.sfp_per_l1
    for index, entry in enumerate(loaded.substation.equipment):
        if entry.part_id is None:
            continue
        part = lookup(loaded.library, entry.part_id)
        for name, value in (entry.overrides.values() if entry.overrides else {}).items():
            found.append(
                Override(
                    subject=f"parts.{entry.id}.{name}",
                    automatic=_text(getattr(part, name)),
                    override=_text(value),
                    field=f"equipment[{index}].overrides.{name}",
                )
            )
        for n, choice in enumerate(entry.sfp):
            port = f"{choice.speed.value} {choice.media.value}"
            if choice.spare is not None:
                automatic = spare_per_l1 if entry.role.value == "l1_switch" else 0
                found.append(
                    Override(
                        subject=f"parts.{entry.id}.sfp.{port}.spare",
                        automatic=str(automatic),
                        override=str(choice.spare),
                        field=f"equipment[{index}].sfp[{n}].spare",
                    )
                )
            if choice.extra:
                found.append(
                    Override(
                        subject=f"parts.{entry.id}.sfp.{port}.extra",
                        automatic="0",
                        override=str(choice.extra),
                        field=f"equipment[{index}].sfp[{n}].extra",
                    )
                )
    return found


def _text(value: object) -> str:
    if value is None:
        return "unset"
    return getattr(value, "value", value).__str__()


def _layout_overrides(loaded: LoadedSubstation) -> list[Override]:
    """Units moved or left out on the Panels board (ADR 0013, R7)."""
    layout = loaded.substation.layout
    found = []
    for index, move in enumerate(layout.overrides):
        if isinstance(move, DeviceMove):
            name, place = move.device, f"panel {move.panel}"
        else:
            assert isinstance(move, PairMove)
            name, place = move.pair, f"panels {move.panel[0]} and {move.panel[1]}"
        if move.position is not None:
            place += f", position {move.position}"
        elif move.top_u is not None:
            place += f", top at {move.top_u} U"
        found.append(
            Override(
                subject=f"layout.{name}",
                automatic="the layout's place",
                override=place,
                field=f"layout.overrides[{index}]",
            )
        )
    for index, unit in enumerate(layout.removed):
        found.append(
            Override(
                subject=f"layout.{unit.device}",
                automatic="in the layout",
                override="left out",
                field=f"layout.removed[{index}]",
            )
        )
    return found


def _spares_overrides(loaded: LoadedSubstation, result: BuildResult) -> list[Override]:
    """Spare quantities set by hand against the policy's (ADR 0035)."""
    edits = loaded.substation.spares_list
    if edits is None or not edits.items:
        return []
    found = []
    for line in spares(loaded, result).lines:
        key = line.ordering_code or line.model
        if not line.overridden or key is None:
            continue
        rule = line.rule_spare
        found.append(
            Override(
                subject=f"spares.{key}",
                automatic=str(rule) if rule is not None else "none (outside the policy)",
                override=str(line.spare),
                risky=rule is not None and line.spare < rule,
                reason=edits.reasons.get(key),
                field=f"spares_list.items.{key}",
            )
        )
    return found


def _switch_counts(loaded: LoadedSubstation) -> list[Override]:
    """The engineer's switch counts per side against the sizing's (plan M72); the sizing
    refuses a count below its own, so these are never risky."""
    network = loaded.substation.network
    if network.l1_per_side is None and network.l2_per_side is None:
        return []
    from bomgen.engine.layout import layout_preview  # the sizing runs with the layout

    try:
        plan = layout_preview(loaded).plan
    except EngineError:
        return []
    found = []
    for level, own, needed in (
        ("l1", network.l1_per_side, plan.l1_needed),
        ("l2", network.l2_per_side, plan.l2_needed),
    ):
        if own is not None:
            found.append(
                Override(
                    subject=f"network.{level}_per_side",
                    automatic=str(needed),
                    override=str(own),
                    field=f"network.{level}_per_side",
                )
            )
    return found
