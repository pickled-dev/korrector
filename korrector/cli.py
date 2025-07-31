import argparse
import logging
import sys

import colorlog

from korrector import (
    korrect_comic_info_path,
    korrect_database,
    korrect_database_oneshots,
)

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Korrector CLI")
    parser.add_argument(
        "db_path",
        nargs="?",
        default=None,
        help="Path to Komga database file",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="adds verbose output",
    )
    parser.add_argument(
        "--backup",
        dest="backup",
        help="Directory to store database backup",
    )
    parser.add_argument(
        "-o",
        "--comicinfo-oneshots",
        dest="oneshots",
        help="Adjust fields inside ComicInfo.xml of cbz in target dir to allow Komga "
        "CBL import to find one-shots",
    )
    parser.add_argument(
        "-O",
        "--korrect-oneshots",
        dest="korrect_oneshots",
        action="store_true",
        help="Adjust the tables in the Komga db to allow Komga CBL import to find"
        " one-shots",
    )
    parser.add_argument(
        "-D",
        "--korrect-database",
        dest="korrect_database",
        action="store_true",
        help="Adjust the tables in the Komga db to facilitate importing reading lists, "
        "not including one-shots",
    )
    parser.add_argument(
        "-d",
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
        "-r",
        "--replace",
        dest="replace",
        help="comma separated string of path replacements for use with containerized"
        " installations. Ex. you would pass'data,/data/print/comics' if your container"
        " mounts /data/print/comics as a volume at /data",
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

    if args.oneshots and args.korrect_database:
        parser.error("-o cannot be used with -O or -D")
    if args.oneshots and args.korrect_oneshots:
        parser.error("-o cannot be used with -O or -D")
    if args.oneshots:
        korrect_comic_info_path(args.oneshots, args.dry_run)
    if args.korrect_database:
        korrect_database(
            args.db_path,
            args.backup,
            args.dry_run,
            args.yes,
        )
    if args.korrect_oneshots:
        korrect_database_oneshots(
            args.db_path,
            args.dry_run,
            args.replace,
        )
    sys.exit(0)


if __name__ == "__main__":
    main()
