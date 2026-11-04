# 0038. RedBox and media converter roles

- Status: Accepted (Ali, 2026-11-04)
- Date: 2026-11-04
- Spec sections: Inputs the tool needs (device library, panel definition), Automatic panel layout
  (Where in the panel), Tag naming conventions

## Context

The engineering workflow review (step 3, Network sizing) asks for "a PRP RedBox or media converter
role" so that a mixed network can be drawn: a single-port device joined to both LANs, or a copper
device brought onto the fibre network. Today such a part can only be entered as a `gateway` or a
`network_switch`, which gives it the wrong label, the wrong tag type and, as a switch, a place in
the sizing it does not have. ADR 0031 keeps redundancy to the duplicated LAN-A/B: PRP and HSR are
refused until a rule for them is written. Plan M73 is this ADR's milestone.

## Decision

1. **Two library categories,** `redbox` and `media_converter`. A record is an ordinary device
   record: ports, power, supply, height (0 for DIN rail) and `tag_type`; the suggested type codes
   are `RBX` and `MC`. Both print in BOM group B like the other devices and carry a device tag
   (the tagged categories of ADR 0030).
2. **Two equipment roles,** `redbox` and `media_converter`, sized as `other`: quantity, `redundant`
   or one side, DC feeds and branch MCBs, power and heat by the existing rules. Parts' **Add a
   device** offers both categories, and the row is named "RedBox" or "Media converter".
3. **The network link is the row's own L2 link** (`l2_ports`, `l2_speed`, `l2_media`, M31). A
   RedBox row is one device on side `none`, so it takes its ports on the L2 switch of each side; a
   media converter takes them on the side or sides it is on. The defaults per unit are 1 port at
   100M MM for a RedBox and 1 port at 1G MM for a media converter. Neither counts as an IED on the
   L1 switches, and the device behind it is not counted either: a schedule row for it says where it
   lands, as today.
4. **In the panel** both stack with the network devices (priority 2) and may have a cable manager
   like a firewall, off by default. A DIN-rail record (height 0) takes no rack unit.
5. **No new redundancy rule.** A RedBox here joins one device to the duplicated LANs A and B. PRP
   and HSR stay refused as ADR 0031 says; a design basis that names them is still rejected.
6. **SFPs.** A converter's fibre port is a port of its library record. An SFP for an SFP slot on
   either part is not counted by the SFP rule (that rule covers switches); add it as an extra or as
   loose material.

## Consequences

- A mixed network is drawn with the right names, tags, MCBs, power and heat, and the L2 sizing
  counts its ports. The example sets neither role, so its golden values do not move.
- psa-devices ships no RedBox or converter yet; a test library part covers the milestone, and the
  library work adds real parts through the normal intake (ADR 0037).
- If PRP or HSR is accepted later, a RedBox will need a rule of its own (both LAN ports on one PRP
  pair); this ADR does not decide it.
