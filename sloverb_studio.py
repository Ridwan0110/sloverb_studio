"""Main entry point for SlowVerb Studio desktop application."""

import os
import sys
import flet as ft

from slowverb import __version__
from slowverb.ui import SlowVerbApp


def parse_cli_args(argv: list[str]) -> bool:
    """
    Handles early CLI flags like --version, --help, --check.
    Returns True if a command-line flag was handled and the application should exit.
    """
    if len(argv) > 1:
        first_arg = argv[1].strip()
        if first_arg in ("--version", "-V", "-v", "version"):
            print(f"SloVerb Studio v{__version__}")
            return True
        return False
    return False


def main(page: ft.Page):
    """Flet application bootstrap."""
    app = SlowVerbApp(page)

    # If an audio file was passed via command line argument, load it directly
    if len(sys.argv) > 1:
        cli_file = sys.argv[1]
        if os.path.isfile(cli_file):
            app.load_file(cli_file)

    return app


def start_app():
    """Starts the SlowVerb Studio desktop application using Flet."""
    # When packaged with PyInstaller, configure assets path to bundled directory
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled_assets = os.path.join(sys._MEIPASS, "assets")
        if os.path.isdir(bundled_assets):
            os.environ.setdefault("FLET_ASSETS_DIR", bundled_assets)

    if hasattr(ft, "run"):
        return ft.run(main)
    elif hasattr(ft, "app"):
        return ft.app(target=main)
    else:
        raise AttributeError("Neither ft.run nor ft.app found in flet module")


if __name__ == "__main__":
    if parse_cli_args(sys.argv):
        sys.exit(0)
    start_app()
