import argparse
import logging

import colorlog

from korrector import (
    copy_share_to_sort,
    korrect_comic_info_path,
    korrect_database,
    korrect_database_oneshots,
)

logger = logging.getLogger(__name__)


def add_copy_share_arguments(parser: argparse.ArgumentParser) -> None:
    copy_share_parser = parser.add_parser(
        "copy-share",
        help="Options for copying files from DC++ share to sort directory"
        "korrector copy-share [share_root] [library_root] [sort_root]",
    )
    copy_share_parser.add_argument(
        "share_root",
        help="Root of the DC++ share",
    )
    copy_share_parser.add_argument(
        "library_root",
        help="Root of the main comics library",
    )
    copy_share_parser.add_argument(
        "sort_root",
        help="Root of the to-sort folder",
    )
    copy_share_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )


def handle_copy_share(args: argparse.Namespace) -> None:
    if not args.share_root or not args.library_root or not args.sort_root:
        msg = "All share, library, and sort roots must be specified"
        raise ValueError(msg)
    copy_share_to_sort(
        args.share_root,
        args.library_root,
        args.sort_root,
        args.dry_run,
    )


def add_korrect_komga_arguments(parser: argparse.ArgumentParser) -> None:
    korrect_komga_parser = parser.add_parser(
        "korrect-komga",
        help="Options for correcting comic information in Komga database",
    )
    korrect_komga_parser.add_argument(
        "db_path",
        nargs="?",
        default=None,
        help="Path to Komga database file",
    )
    korrect_komga_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="adds verbose output",
    )
    korrect_komga_parser.add_argument(
        "-b",
        "--backup",
        dest="backup",
        help="Directory to store database backup",
    )
    korrect_komga_parser.add_argument(
        "-d",
        "--korrect-database",
        dest="korrect_database",
        action="store_true",
        help="Adjust the tables in the Komga db to facilitate importing reading lists, "
        "not including one-shots",
    )
    korrect_komga_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    korrect_komga_parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Accept all default prompts",
    )
    korrect_komga_parser.add_argument(
        "-r",
        "--replace",
        dest="replace",
        help="comma separated string of path replacements for use with containerized"
        " installations. Ex. you would pass'data,/data/print/comics' if your container"
        " mounts /data/print/comics as a volume at /data",
    )
    korrect_komga_parser.add_argument(
        "-o",
        "--korrect-oneshots",
        dest="korrect_oneshots",
        action="store_true",
        help="Use db to find one-shots cbz files and correct their ComicInfo.xml."
        "Consider using -r if you are running Komga in a containerized environment.",
    )


def handle_korrect_komga(args: argparse.Namespace) -> None:
    if not args.db_path:
        msg = "Database path must be specified"
        raise ValueError(msg)
    if args.korrect_database and args.korrect_oneshots:
        msg = "-d cannot be used with -o"
        raise ValueError(msg)
    if args.replace and not args.korrect_oneshots:
        msg = "-r can only be used with -o"
        raise ValueError(msg)
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


def add_korrect_comic_info_arguments(parser: argparse.ArgumentParser) -> None:
    korrect_comic_info_parser = parser.add_parser(
        "korrect-comic-info",
        help="Options for correcting comic information in Komga database",
    )
    korrect_comic_info_parser.add_argument(
        "oneshots",
        help="Path to a dir containing one-shot CBZ files to correct ComicInfo.xml",
    )
    korrect_comic_info_parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    korrect_comic_info_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="adds verbose output",
    )


def handle_korrect_comic_info(args: argparse.Namespace) -> None:
    if not args.oneshots:
        msg = "Oneshots directory must be specified"
        raise ValueError(msg)
    korrect_comic_info_path(
        args.oneshots,
        args.dry_run,
    )


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
    add_copy_share_arguments(subparsers)
    add_korrect_komga_arguments(subparsers)
    add_korrect_comic_info_arguments(subparsers)
    args = parser.parse_args()

    # setup logging based on verbosity
    setup_logging(args.verbose)

    # handle subcommands
    try:
        if args.command == "copy-share":
            handle_copy_share(args)
        elif args.command == "korrect-komga":
            handle_korrect_komga(args)
        elif args.command == "korrect-comic-info":
            handle_korrect_comic_info(args)
    except Exception:
        logger.exception(
            "Error occurred while processing command '%s'",
            args.command,
        )


if __name__ == "__main__":
    main()
