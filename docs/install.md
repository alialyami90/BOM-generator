# Installing BOM Generator on Windows

Requirements: 64-bit Windows 10 (21H2 or later) or Windows 11. No admin rights
are needed; the app installs for your Windows user only.

1. Download `bomgen-setup-<version>.exe` from the latest
   [GitHub Release](https://github.com/alialyami90/BOM-generator/releases/latest).
2. Run it. The installer isn't code-signed yet (plan Q19), so Windows
   SmartScreen may say "Windows protected your PC". Click **More info**, check
   the publisher and file name, then click **Run anyway**.
3. Follow the wizard. The app goes to `%LOCALAPPDATA%\Programs\BOM Generator`
   and gets a Start-menu entry.

The install folder also holds `bomgen.exe`, the command-line tool, for use from
a terminal (`"%LOCALAPPDATA%\Programs\BOM Generator\bomgen.exe" --version`).

## Library update packages

Double-click a `.bomlib` file to import it (ADR 0008). The app installs the
library and shows what changed, or says why it refused the package (a
downgrade, a damaged file, a library newer than the app). A `.bomproj` project
file opens the app on that project.

## Updating and uninstalling

Run a newer installer over the old one to update. Uninstall from **Settings →
Apps → Installed apps → BOM Generator**. Uninstalling keeps your installed
device libraries in `%LOCALAPPDATA%\bomgen\`; delete that folder to remove them
too.
