"""What an update changes: parts added, changed and removed, by `part_id` (plan M8).

The library is read as plain YAML so this module does not depend on the input
models; full schema validation is the loader's job.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import yaml

from bomgen.library_store.errors import LibraryPackageError
from bomgen.library_store.manifest import LIBRARY_FILE


def parse_library(data: bytes) -> dict[str, Any]:
    """Parse `library.yaml` and check the shape the diff relies on."""
    try:
        library = yaml.safe_load(data.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise LibraryPackageError(f"{LIBRARY_FILE} is not valid YAML: {exc}") from exc
    if not isinstance(library, dict):
        raise LibraryPackageError(f"{LIBRARY_FILE} must be a mapping with a 'devices' list")
    devices = library.get("devices") or []
    if not isinstance(devices, list) or not all(isinstance(d, dict) for d in devices):
        raise LibraryPackageError(f"{LIBRARY_FILE}: 'devices' must be a list of mappings")
    if not isinstance(library.get("catalogues") or {}, dict):
        raise LibraryPackageError(f"{LIBRARY_FILE}: 'catalogues' must be a mapping")
    seen: set[str] = set()
    for index, device in enumerate(devices):
        part_id = device.get("part_id")
        if not isinstance(part_id, str) or not part_id:
            raise LibraryPackageError(f"{LIBRARY_FILE}: devices[{index}] has no part_id")
        if part_id in seen:
            raise LibraryPackageError(f"{LIBRARY_FILE}: duplicate part_id {part_id!r}")
        seen.add(part_id)
    return library


@dataclass(frozen=True)
class LibraryDiff:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: dict[str, list[str]] = field(default_factory=dict)
    catalogues_changed: list[str] = field(default_factory=list)
    files_added: list[str] = field(default_factory=list)
    files_changed: list[str] = field(default_factory=list)
    files_removed: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (
            self.added
            or self.removed
            or self.changed
            or self.catalogues_changed
            or self.files_added
            or self.files_changed
            or self.files_removed
        )

    def summary_lines(self) -> list[str]:
        if self.is_empty:
            return ["No changes."]
        lines: list[str] = []
        if self.added:
            lines.append(f"Added parts ({len(self.added)}): {', '.join(self.added)}")
        if self.removed:
            lines.append(f"Removed parts ({len(self.removed)}): {', '.join(self.removed)}")
        if self.changed:
            lines.append(f"Changed parts ({len(self.changed)}):")
            lines.extend(f"  {part}: {', '.join(fields)}" for part, fields in self.changed.items())
        if self.catalogues_changed:
            lines.append(f"Changed catalogues: {', '.join(self.catalogues_changed)}")
        for label, paths in (
            ("Added files", self.files_added),
            ("Changed files", self.files_changed),
            ("Removed files", self.files_removed),
        ):
            if paths:
                lines.append(f"{label}: {', '.join(paths)}")
        return lines


def _devices(library: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    if library is None:
        return {}
    return {device["part_id"]: device for device in library.get("devices") or []}


def _changed_keys(old: Mapping[str, Any], new: Mapping[str, Any]) -> list[str]:
    return sorted(key for key in old.keys() | new.keys() if old.get(key) != new.get(key))


def _brand_changes(old: Mapping[str, Any], new: Mapping[str, Any]) -> list[str]:
    """`kind:id` of each brand set that was added, removed or edited (ADR 0017 catalogue brands)."""
    old_brands = (old or {}).get("catalogue_brands") or {}
    new_brands = new.get("catalogue_brands") or {}
    changed: list[str] = []
    for kind in old_brands.keys() | new_brands.keys():
        before = {b.get("id"): b for b in old_brands.get(kind) or [] if isinstance(b, dict)}
        after = {b.get("id"): b for b in new_brands.get(kind) or [] if isinstance(b, dict)}
        changed += [
            f"{kind}:{i}" for i in before.keys() | after.keys() if before.get(i) != after.get(i)
        ]
    return changed


def diff_libraries(
    old: Mapping[str, Any] | None,
    new: Mapping[str, Any],
    old_files: Mapping[str, str] | None = None,
    new_files: Mapping[str, str] | None = None,
) -> LibraryDiff:
    """Compare two parsed libraries and, optionally, their manifest file checksums."""
    old_devices, new_devices = _devices(old), _devices(new)
    changed = {
        part: fields
        for part in sorted(old_devices.keys() & new_devices.keys())
        if (fields := _changed_keys(old_devices[part], new_devices[part]))
    }
    old_catalogues = (old or {}).get("catalogues") or {}
    new_catalogues = new.get("catalogues") or {}
    extra_old = {p: d for p, d in (old_files or {}).items() if p != LIBRARY_FILE}
    extra_new = {p: d for p, d in (new_files or {}).items() if p != LIBRARY_FILE}
    return LibraryDiff(
        added=sorted(new_devices.keys() - old_devices.keys()),
        removed=sorted(old_devices.keys() - new_devices.keys()),
        changed=changed,
        catalogues_changed=[
            *_changed_keys(old_catalogues, new_catalogues),
            *sorted(_brand_changes(old or {}, new)),
        ],
        files_added=sorted(extra_new.keys() - extra_old.keys()),
        files_changed=sorted(
            p for p in extra_old.keys() & extra_new.keys() if extra_old[p] != extra_new[p]
        ),
        files_removed=sorted(extra_old.keys() - extra_new.keys()),
    )
