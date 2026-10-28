"""Resolve a mirror panel file against the panel it mirrors.

Follows the spec section "How each panel BOM groups its materials" (last paragraph)
and ADR 0010 item 6.
"""

from __future__ import annotations

import re

from bomgen.models.panel import DeviceInstance, Lan, Panel, PanelMirror, PanelOptions

_LAN_INDEX: dict[str, int] = {"A": 1, "B": 2}


def lan_index(lan: Lan) -> int:
    """The LAN-index suffix used in tags: ``"A"`` is 1, ``"B"`` is 2."""
    return _LAN_INDEX[lan]


def mirror_tag(tag: str, base: Panel, mirror: PanelMirror) -> str:
    """Rewrite a tag of ``base`` for ``mirror``; tags of other origin are returned unchanged."""
    base_prefix = f"{base.tag_prefix}-"
    if not tag.startswith(base_prefix):
        return tag
    rest = tag.removeprefix(base_prefix)
    if base.lan is not None and mirror.lan is not None:
        head, separator, last = rest.rpartition("-")
        if last == str(lan_index(base.lan)):
            last = str(lan_index(mirror.lan))
        else:
            last = re.sub(rf"\b{base.lan}(\d*)\b", rf"{mirror.lan}\1", last)
        rest = f"{head}{separator}{last}"
    return f"{mirror.tag_prefix}-{rest}"


def mirror_panel(base: Panel, mirror: PanelMirror) -> Panel:
    """Build the panel ``mirror`` describes; raises ``ValidationError`` for bad merged options."""
    options = PanelOptions.model_validate(base.options.model_dump() | mirror.options)
    both_have_lan = base.lan is not None and mirror.lan is not None
    devices = [_mirror_device(device, base, mirror, both_have_lan) for device in base.devices]
    port_plans = {mirror_tag(key, base, mirror): plan for key, plan in base.port_plans.items()}
    return base.model_copy(
        update={
            "id": mirror.id,
            "cabinet_number": mirror.cabinet_number,
            "cabinet_name": mirror.cabinet_name,
            "tag_prefix": mirror.tag_prefix,
            "lan": mirror.lan,
            "sheet_name": mirror.sheet_name,
            "devices": devices,
            "port_plans": port_plans,
            "options": options,
            "document": mirror.document,
            "revision": mirror.revision,
        }
    )


def _mirror_device(
    device: DeviceInstance, base: Panel, mirror: PanelMirror, both_have_lan: bool
) -> DeviceInstance:
    update: dict[str, object] = {}
    if device.tag is not None:
        update["tag"] = mirror_tag(device.tag, base, mirror)
    if both_have_lan and device.lan == base.lan:
        update["lan"] = mirror.lan
    return device.model_copy(update=update)
