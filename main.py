"""
main.py
Main entrypoint for Auto Mouse Mover.
"""

import os
import sys

# Auto-resolve .venv site-packages if running from global Python
_venv_site_pkgs = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Lib", "site-packages")
if os.path.isdir(_venv_site_pkgs) and _venv_site_pkgs not in sys.path:
    sys.path.insert(0, _venv_site_pkgs)

from app import run_app

if __name__ == "__main__":
    try:
        run_app()
    except KeyboardInterrupt:
        pass
