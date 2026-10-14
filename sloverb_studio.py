"""Main entry point for SlowVerb Studio desktop application."""

import os
import sys
import flet as ft

from slowverb.ui import SlowVerbApp


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
    if hasattr(ft, "run"):
        return ft.run(main)
    elif hasattr(ft, "app"):
        return ft.app(target=main)
    else:
        raise AttributeError("Neither ft.run nor ft.app found in flet module")


if __name__ == "__main__":
    start_app()
