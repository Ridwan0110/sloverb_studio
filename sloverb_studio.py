"""Main entry point for SlowVerb Studio desktop application."""

import argparse
import os
import sys
from typing import Optional
import flet as ft

from slowverb import __version__
from slowverb.ui import SlowVerbApp


def create_argument_parser() -> argparse.ArgumentParser:
    """Creates the command-line argument parser for SlowVerb Studio."""
    parser = argparse.ArgumentParser(
        prog="sloverb_studio",
        description="SloVerb Studio - Cyber/robotic audio editor for slowed & reverb, nightcore, and bass boosting.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=None,
        help="Optional path to an audio file to load on startup.",
    )
    parser.add_argument(
        "--mobile-ui",
        action="store_true",
        help="Simulate mobile UI layout on desktop.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with diagnostics export.",
    )
    parser.add_argument(
        "-v",
        "-V",
        "--version",
        action="version",
        version=f"SloVerb Studio v{__version__}",
        help="Show program's version number and exit.",
    )
    return parser


def parse_cli_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """
    Parses command-line arguments using argparse.
    Handles --version, --help, --mobile-ui, and optional audio file path.
    """
    if argv is None:
        argv = sys.argv[1:]
    elif argv:
        base_0 = os.path.basename(argv[0]).lower()
        if base_0 in ("sloverb_studio.py", "sloverbstudio.exe", "sloverbstudio") or base_0.endswith(".py"):
            argv = argv[1:]

    # Support 'version' subcommand/alias without hyphen
    if len(argv) == 1 and argv[0] == "version":
        argv = ["--version"]

    parser = create_argument_parser()
    args, _ = parser.parse_known_args(argv)

    if getattr(args, "mobile_ui", False):
        os.environ["SLOVERB_MOBILE_UI"] = "1"

    if getattr(args, "debug", False):
        import slowverb
        slowverb.DEBUG_MODE = True
        os.environ["SLOVERB_DEBUG"] = "1"

    return args


def main(page: ft.Page, cli_args: Optional[argparse.Namespace] = None):
    """Flet application bootstrap."""
    if cli_args is None:
        base_cmd = os.path.basename(sys.argv[0]).lower() if sys.argv else ""
        if "pytest" in sys.modules and base_cmd not in ("sloverb_studio.py", "sloverbstudio.exe", "sloverbstudio"):
            cli_args = argparse.Namespace(file=None, mobile_ui=False)
        else:
            cli_args = parse_cli_args()

    force_mobile = bool(getattr(cli_args, "mobile_ui", False)) or (os.environ.get("SLOVERB_MOBILE_UI") in ("1", "true", "True"))
    debug_mode = bool(getattr(cli_args, "debug", False)) or (os.environ.get("SLOVERB_DEBUG") in ("1", "true", "True"))
    app = SlowVerbApp(page, force_mobile_ui=force_mobile, debug_mode=debug_mode)

    # If an audio file was passed via command line argument, load it directly
    if getattr(cli_args, "file", None) and os.path.isfile(cli_args.file):
        app.load_file(cli_args.file)

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
    parse_cli_args()
    start_app()
