"""CLI entrypoint for the Mosaico catalog TUI."""

import argparse
import os

from mosaicolabs.logging_config import setup_sdk_logging

from .app import MosaicoCatalogApp


def _resolve_host_port(args: argparse.Namespace) -> tuple[str, int]:
    host = args.host or os.getenv("MOSAICO_HOST", "localhost")

    if args.port is not None:
        return host, args.port

    env_port = os.getenv("MOSAICO_PORT", "6726")
    try:
        return host, int(env_port)
    except ValueError as exc:
        raise ValueError(f"Invalid MOSAICO_PORT value '{env_port}'.") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Browse remote Mosaico sequences/topics and metadata in a TUI.",
    )
    parser.add_argument("--host", help="Mosaico server host")
    parser.add_argument("--port", type=int, help="Mosaico server port")
    parser.add_argument(
        "--log",
        default="WARNING",
        type=str.upper,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="SDK logging level",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        host, port = _resolve_host_port(args)
    except ValueError as exc:
        parser.error(str(exc))

    setup_sdk_logging(level=args.log, pretty=False)

    app = MosaicoCatalogApp(host=host, port=port)
    app.run()


if __name__ == "__main__":
    main()
