# 0023. Separate AC and DC MCB choices

- Status: Proposed
- Date: 2026-10-28
- Spec sections: Inputs the tool needs (1. Device library; commodity catalogues),
  Electrical rules (branch MCBs)

## Context

ADR 0017 gives each catalogue one brand choice, so `catalogue_choice.mcb` sizes the AC
branches and the 125 V DC branches alike. Q37 keeps the iC60N as the default, which is rated
to exactly 125 V DC while the battery floats at about 140 V. The DC-rated ranges (for
example Schneider C60H-DC) are brand sets (#130), but some of them are DC only, so picking
one as `mcb` would size the AC branches wrongly. #145 refuses a brand with `ac_rated: false`
as `mcb`. Ali chose separate AC and DC choices (Q39).

## Decision

1. **Choice key `mcb_dc`.** `catalogue_choice` gains `mcb_dc`, which names a brand from
   `catalogue_brands.mcb` (the same list as `mcb`) or `default`. It merges key by key like
   the other keys (ADR 0017 point 3). `mcb` keeps sizing the AC branches.
2. **Fallback.** When `mcb_dc` is unset, the DC set follows the `mcb` choice, as it does
   today. Existing projects, the example and the golden values do not change.
3. **`mcb_dc: default`** means the library's default DC set (point 5), even when `mcb`
   names another brand. That lets a project change the AC brand and keep the default for DC.
4. **The DC choice must be DC-rated.** The loader reports a located error when a written
   `mcb_dc` resolves to a set without `dc_rating_v`, and it lists the brands that have one.
   Whether the rating covers the float voltage stays the check report's job (Q37, the
   `dc_float` check). A DC-only brand (`ac_rated: false`, #145) is a valid `mcb_dc`.
   Unset and `default` therefore differ once `mcb` names a brand. With a library whose
   default is the iC60N and with ABB S200M as a brand:
   - `{mcb: abb-s200m}` (`mcb_dc` unset) sizes AC and DC with the ABB S200M.
   - `{mcb: abb-s200m, mcb_dc: default}` sizes AC with the ABB S200M and DC with the iC60N.
   - `{mcb: abb-s200m, mcb_dc: schneider-c60h-dc}` sizes DC with the C60H-DC.
5. **Resolved sets.** `Catalogues` gains `mcb_dc` (optional). The loader puts the chosen DC
   set there as a plain `McbCatalogue`. `Catalogues.dc_mcb` gives `mcb_dc`, else `mcb`. A
   library file may set `catalogues.mcb_dc` as its own default DC set, which must have
   `dc_rating_v`. The example library does not set it.

## Consequences

- The engine must size the DC branches from `catalogues.dc_mcb` instead of `catalogues.mcb`
  (`engine/dc_dist.py`, `engine/mcb.py`, and the `dc_float` check in `checks.py`). That
  work belongs to role 9 and follows this change. Until then, `mcb_dc` loads and is checked
  but does not yet change the BOM.
- The DC MCBs' auxiliary contacts still come from `aux_contact`. A DC brand whose contacts
  differ needs its own `aux_contact` choice.
- The library CSV (ADR 0018) and the app's settings forms do not show `mcb_dc` yet.
