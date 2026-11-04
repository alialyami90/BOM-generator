"""The spares list: from the Summary BOM, a spare quantity per line in the policy's
categories, then the substation's overrides, exclusions and extras (ADR 0035, plan M64).

A policy line gets ``max(minimum, ceil(percent * installed))``; a zero is left out. A
line is keyed by its ordering code, or its model when it has none. Only library parts
have a category, so catalogue lines (MCBs, terminal blocks) get a spare by override only.
"""

import math
from fractions import Fraction

from bomgen.engine.summary import summarize
from bomgen.engine.units import describe, lookup
from bomgen.io.loader import LoadedSubstation
from bomgen.models.bom import BomLine, BuildResult, SpareLine, SparesTable, SummaryLine
from bomgen.models.calc import LineRef
from bomgen.models.library import Category
from bomgen.models.substation import SpareExtra, SparesPolicy


def spares(loaded: LoadedSubstation, result: BuildResult) -> SparesTable:
    basis = loaded.substation.design_basis
    policy = basis.spares_policy if basis else None
    edits = loaded.substation.spares_list
    overrides = edits.items if edits else {}
    excluded = set(edits.excluded) if edits else set()
    lines: list[SpareLine] = []
    for index, line in enumerate(summarize(result).lines):
        key = line.ordering_code or line.model
        if not isinstance(line.qty, int) or key is None or key in excluded:
            continue
        rule = _rule(line, _category(loaded, result, line), policy)
        if key in overrides:
            spare = overrides[key]
            text = f"set to {spare}" + (f" (rule gives {rule.spare})" if rule else "")
            lines.append(_line(line, index, spare, text, overridden=True))
        elif rule is not None and rule.spare:
            lines.append(rule.model_copy(update={"summary_line": index}))
    lines.extend(_extra(loaded, extra) for extra in (edits.extra if edits else []))
    return SparesTable(lines=tuple(lines))


def _category(loaded: LoadedSubstation, result: BuildResult, line: SummaryLine) -> Category | None:
    part_id = _bom_line(result, line.sources[0].ref).part_id
    return lookup(loaded.library, part_id).category if part_id else None


def _bom_line(result: BuildResult, ref: LineRef) -> BomLine:
    if ref.panel_id is None:
        assert result.loose is not None
        return result.loose.lines[ref.line]
    return next(p for p in result.panels if p.panel_id == ref.panel_id).lines[ref.line]


def _rule(
    line: SummaryLine, category: Category | None, policy: SparesPolicy | None
) -> SpareLine | None:
    if policy is None or category is None or category not in policy.categories:
        return None
    assert isinstance(line.qty, int)
    percent = policy.percent.get(category, 0)
    minimum = policy.minimum_per_part
    spare = max(minimum, math.ceil(Fraction(str(percent)) * line.qty / 100))
    text = f"{percent:g}% of {line.qty}, min {minimum} = {spare}"
    return _line(line, None, spare, text, percent=percent, minimum=minimum)


def _line(
    line: SummaryLine, index: int | None, spare: int, basis: str, **rule: object
) -> SpareLine:
    return SpareLine.model_validate(
        {
            "description": line.description,
            "installed": line.qty,
            "spare": spare,
            "make": line.make,
            "model": line.model,
            "ordering_code": line.ordering_code,
            "basis": basis,
            "summary_line": index,
        }
        | rule
    )


def _extra(loaded: LoadedSubstation, extra: SpareExtra) -> SpareLine:
    if extra.part_id is None:
        assert extra.description is not None
        return SpareLine(
            description=extra.description, installed=None, spare=extra.qty, basis="added"
        )
    part = lookup(loaded.library, extra.part_id)
    return SpareLine(
        description=describe(part, None, None),
        installed=None,
        spare=extra.qty,
        make=part.make,
        model=part.model,
        ordering_code=part.ordering_code,
        basis="added",
    )
