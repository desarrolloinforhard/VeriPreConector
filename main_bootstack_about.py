"""Entry point empaquetable del piloto Acerca de con Bootstack."""

from __future__ import annotations

import sys

from main_bootstack import main


if __name__ == "__main__":
    main(["--about-pilot", *sys.argv[1:]])
