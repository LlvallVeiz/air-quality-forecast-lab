#!/usr/bin/env python3
"""Entry point: `python main.py <subcommand> ...` (see `aqflab.cli`)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aqflab.cli import main

if __name__ == "__main__":
    sys.exit(main())
