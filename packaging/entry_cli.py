"""PyInstaller entry script for the console CLI, ``bomgen.exe`` (see bomgen.spec)."""

import sys

from bomgen.app.launcher import cli_main

sys.exit(cli_main())
