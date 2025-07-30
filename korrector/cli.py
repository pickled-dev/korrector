import argparse
import logging
import sys

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
        "--korrect-oneshots",
        dest="oneshots",
        action="store_true",
        help="Adjust fields inside of ComicInfo.xml files for one-shots",
    )
    parser.add_argument(
        "--korrect-database",
        dest="korrect_database",
        action="store_true",
        help="Adjust the tables in the Komga db to facilitate importing reading lists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO

    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(message)s",
    )

    if args.oneshots:
        korrect_oneshots(args.db_path, args.dry_run)
    if args.korrect_database:
        korrect_database(args.db_path, args.backup, args.dry_run)
    sys.exit(0)


if __name__ == "__main__":
    main()
