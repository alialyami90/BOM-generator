"""PyInstaller entry script for the windowed app, ``BOM Generator.exe`` (see bomgen.spec)."""

import sys

from bomgen.app.launcher import app_main

sys.exit(app_main())
