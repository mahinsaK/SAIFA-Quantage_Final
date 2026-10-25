"""Thin Streamlit launcher for the SAIFA dashboard."""

from pathlib import Path

from saifa.dashboard.app import main as _main

ROOT = Path(__file__).resolve().parent


def main(root: Path = ROOT) -> None:
    _main(root)


if __name__ == "__main__":
    main()
