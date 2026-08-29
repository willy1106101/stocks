"""Development launcher for the desktop application.

Kept for convenience, but it intentionally runs the same port-free pywebview
application as the packaged executable.
"""

import runpy


if __name__ == "__main__":
    runpy.run_module("desktop_app", run_name="__main__")
