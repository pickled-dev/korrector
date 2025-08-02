import argparse
import logging

import colorlog

from korrector.main import (
    korrect_database,
)

LOGGER = logging.getLogger(__name__)


def add_korrect_komga_arguments(parser: argparse.ArgumentParser) -> None:
    korrect_komga_parser = parser.add_parser(
        "korrect-komga",
        help="Options for correcting comic information in Komga database",
    )
    korrect_komga_parser.add_argument(
        "-d",
        "--korrect-database",
        dest="korrect_database",
        action="store_true",
        help="Adjust the tables in the Komga db to facilitate importing reading lists, "
        "not including one-shots",
    )


def handle_korrect_komga(args: argparse.Namespace) -> None:
    korrect_database(args.dry_run)


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)s:%(name)s: %(message)s",
            log_colors={
                "DEBUG": "white",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        ),
    )
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[handler],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Korrector CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # setup subparsers for each command
    add_korrect_komga_arguments(subparsers)
    args = parser.parse_args()

    # setup logging based on verbosity
    try:
        setup_logging(args.verbose)
    except AttributeError:
        setup_logging(False)

    # handle subcommands
    try:
        if args.command == "korrect-komga":
            handle_korrect_komga(args)
    except Exception:
        LOGGER.exception(
            "Error occurred while processing command '%s'",
            args.command,
        )


if __name__ == "__main__":
    main()
