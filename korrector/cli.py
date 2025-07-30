import argparse
import logging
import sys

import colorlog

from korrector import korrect_database, korrect_oneshots

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Korrector CLI")
    parser.add_argument("db_path", help="Path to Komga database file")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="adds verbose output",
    )
    parser.add_argument("--backup", help="Directory to store database backup")
    parser.add_argument(
        "-o",
        "--korrect-oneshots",
        dest="oneshots",
        action="store_true",
        help="Adjust fields inside of ComicInfo.xml files for one-shots",
    )
    parser.add_argument(
        "-d",
        "--korrect-database",
        dest="korrect_database",
        action="store_true",
        help="Adjust the tables in the Komga db to facilitate importing reading lists",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Accept all default prompts",
    )
    parser.add_argument(
        "-p",
        "--prefix",
        help="Prefix to substitute in database path",
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO

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

    if args.oneshots:
        korrect_oneshots(args.db_path, args.dry_run, args.prefix)
    if args.korrect_database:
        korrect_database(args.db_path, args.backup, args.dry_run, args.yes)
    sys.exit(0)


if __name__ == "__main__":
    main()
