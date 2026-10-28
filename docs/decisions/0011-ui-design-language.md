# 0011. UI design language and bundled fonts

- Status: Accepted (Ali, 2026-10-28)
- Date: 2026-10-28
- Spec sections: — (the app is outside the spec; requested by Ali in the project thread)

## Context

M9 designs the Windows desktop app (ADR 0007). Ali asked for an industrial
feel using the colours and fonts of SEL's site and software, and supplied
screenshots. The look has to be reproducible without a licence problem: the
installer ships its own fonts, and the app must not look like a product of the
vendor it takes inspiration from.

## Decision

1. **Palette from the screenshots, as inspiration only.** Deep navy `#003B5D`
   (top bar, headings), cobalt `#1A3FD8` (actions, links, focus), cool
   off-white `#F2F5FA` (ground), slate for text, red for problems only. Sampled
   from the screenshots; recorded as tokens in `docs/ui/tokens.json`. No
   vendor logo, name, product imagery or trademarked wording appears in the
   app, and the app has its own plain wordmark.
2. **Fonts: Hanken Grotesk and JetBrains Mono, both bundled.** The reference
   typeface is not identified and may be licensed, so it is not used. Hanken
   Grotesk (variable, Latin subset) matches its light, airy neo-grotesque feel
   and covers all UI text. JetBrains Mono (variable, Latin subset) is used only
   for part ids, tags, codes, YAML and paths. Both are SIL Open Font License
   1.1, which allows bundling and requires the licence text to ship with the
   fonts.
3. **Where the files live.** `docs/ui/fonts/` holds the two `.woff2` files and
   their licence texts (`LICENSE-hanken-grotesk.txt`,
   `LICENSE-jetbrains-mono.txt`). In M10 they move to `src/bomgen/app/ui/fonts/`
   with the licence files beside them, and the installer includes both.
   Fonts are loaded from the app's own files, never from a web host.
4. **Themes.** Light first, dark from the same semantic token roles, following
   the Windows setting unless the user chooses.
5. **Signature.** A "readiness rail": the navigation shows each step's status
   (tick, count, version, error count, Blocked or Ready), repeated in the status
   bar.
6. **Source of truth.** `docs/ui/tokens.json` (W3C design tokens). The
   prototype's `tokens.css` is generated from it by `docs/ui/tools/build-tokens.mjs`;
   M10 generates its CSS the same way.

## Consequences

- The app looks related to its industry without borrowing a vendor's brand.
- No font licence to buy or track; the OFL texts must stay beside the font
  files in the repository and the installer.
- If Ali later supplies the exact reference font or a licence for it, only the
  `fontFamily` tokens and the bundled files change.
- The Latin subset is enough for English. Arabic or other scripts would need
  additional subsets and an RTL review (brief: English only for now).
