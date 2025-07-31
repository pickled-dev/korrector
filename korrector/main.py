"""Korrector package: tools for Komga database correction.

This package provides a way to take a Komga database and alter the names of books in
the database to more easily facilitate the importation of DieselTech's reading lists.

Doesn't alter anything that can't be changed by a user in the Web UI. Only works as
intended if the comics have been tagged properly with either Metron of ComicVine
(though I've only tested with Metron).

For one-shots the ComicInfo.xml file must be read, so the script will extract the
ComicInfo.xml to read it, but will not alter it.

Backup your database before running this script, just in case something goes wrong.
Use the `--backup` and specify a directory create a backup of the database before
running the script.
"""

import io
import logging
import pathlib
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

import sqlalchemy.orm as alch
from lxml import etree
from sqlalchemy import create_engine

from .orm import Book, BookMetadata, Series

logger = logging.getLogger(__name__)


def copy_share_to_sort(
    share_root: Path = Path("/data/dc++"),
    library_root: Path = Path("/data/print/comics"),
    sort_root: Path = Path("/data/to-sort"),
    dry_run: bool = False,
) -> None:
    """Copy files not present in library from share to temp directory, mirror structure.

    This function iterates over all directories in the DC++ root directory, and copies
    comic files (.cbz) to a temporary directory for sorting. It mirrors the directory
    structure of the DC++ root directory in the temporary directory. If a folder in the
    DC++ root directory has the same or more comic files than the corresponding folder
    in the library root directory, that folder is skipped. The files are copied with
    their original filenames from the DC++ share.

    Args:
        share_root (Path): Root of the DC++ share.
        library_root (Path): Root of the main comics library.
        sort_root (Path): Root of the to-sort folder.
        dry_run (bool): If True, do not actually copy files.

    Notes:
        - Only folders with comic files (.cbz, .cbr, .pdf) are considered.
        - If the corresponding library folder has the same or more comic files,
          that folder is skipped.
        - Files are copied with their DC++ filenames.

    """
    # iterate over all directories in the DC++ root
    for dirpath, filenames in pathlib.Path(share_root).iterdir():
        comic_files = [f for f in filenames if f.lower().endswith(".cbz")]
        if not comic_files:
            continue

        # build the full paths for the library and to-sort directories
        rel_path = Path(dirpath).relative_to(share_root)
        library_path = library_root / rel_path
        to_sort_path = sort_root / rel_path

        # recursivley add all cbz files in mirrored library directory to a list
        library_files = [
            f
            for f in pathlib.Path(library_path).iterdir()
            if f.lower().endswith(".cbz")
        ]
        if len(library_files) >= len(comic_files):
            logger.info(
                "Skipping folder %s: library has %d files, DC++ has %d",
                rel_path,
                len(library_files),
                len(comic_files),
            )
            continue

        if not dry_run:
            to_sort_path.mkdir(parents=True, exist_ok=True)

        # copy files from DC++ to the to-sort directory
        for fname in comic_files:
            src = Path(dirpath) / fname
            dst = to_sort_path / fname
            if not dst.exists():
                logger.info("Copying %s -> %s", src, dst)
            if not dry_run:
                shutil.copy2(src, dst)


def backup(komga_db_path: str, komga_backup: str) -> None:
    """Backup the Komga database to a specified backup path.

    Args:
        komga_db_path (str): The path to the Komga database.
        komga_backup (str): The path where the backup should be stored.

    """
    backup_name = f"{datetime.now().strftime('%Y-%m-%d(%H_%M_%S)')}.sqlite"
    src = f"{komga_db_path}"
    dest = f"{komga_backup}/{backup_name}"
    shutil.copy(src, dest)


def get_release_year(series: Series, yes: bool = False) -> str:
    """Get the release year for a series.

    If the first issue is available, it will return the release year of that issue.
    If the first issue is not available, it will attempt to guess the year from the
    series name. If no year can be found, it will prompt the user to enter the year
    manually.

    Args:
        series (Series): The series to get the release year for.
        yes (bool, optional): If True, will prompt the user to enter the year manually.

    Returns:
        str: The release year as a string.

    Raises:
        ValueError: If no year can be found.

    """
    # return year of issue numbered 1 if available
    first: BookMetadata | None = next(
        (
            book.book_metadata
            for book in series.books
            if book.book_metadata and book.book_metadata.number == "1"
        ),
        None,
    )
    if first is not None:
        pattern = re.compile(r"\d{4}-\d{2}-\d{2}")
        if not first.release_date or not pattern.match(first.release_date):
            msg = f"Invalid release date for {series.name}: {first.release_date}"
            raise ValueError(msg)
        release_date = first.release_date
        return release_date.split("-")[0]

    # Guess the year from the series name if no first issue is found
    match = re.search(r"\((\d{4})\)", series.name)
    if match is None:
        msg = f"No first issue, or year, found in {series.name}"
        raise ValueError(msg)
    year = match.group(1)

    # prompt user offering guess year as default
    if yes:
        return year
    response = input(
        f"No first issue found for {series.name}. \
            Enter year manually (Default: {year}): ",
    )
    return response or year


def make_korrection(series: Series, yes: bool = False) -> None:
    """Alter a series in the komga database to make it easier to import.

    The desired format for the TITLE field in the SERIES_METADTA tablse is:
    "Title (YYYY)"

    Args:
        series (Series): The series to make the korrection for.
        yes (bool, optional): If True, will prompt the user to enter the year manually.

    Raises:
        ValueError: If the series is already correct, or if the series is locked.

    """
    meta = series.series_metadata
    meta_title = meta.title
    if meta_title and "(" in meta_title and ")" in meta_title:
        msg = f"{series.name} is already correct [{meta_title}]"
        raise ValueError(msg)
    if meta.title_lock:
        msg = f"{series.name} is manually locked by user."
        raise ValueError(msg)
    title = f"{meta.title} ({get_release_year(series, yes)})"
    logger.info("Korrection: [%s] (%s) -> (%s)", series.name, meta.title, title)
    meta.title = title


def korrect_database(
    komga_db: str,
    backup_path: str = "",
    dry_run: bool = False,
    yes: bool = False,
) -> str:
    """Read a Komga db, and alter the names of books in the db.

    Args:
        komga_db (str): The path to the Komga database file.
        backup_path (str, optional): Path where a backup of the db should be stored.
        dry_run (bool, optional): If True, no changes will be made to the db.
        yes (bool, optional): If True, will prompt the user to enter the year manually.

    Returns:
        str: A message indicating that the korrection has completed successfully.

    """
    if backup_path:
        backup(komga_db, backup_path)
    engine = create_engine(f"sqlite:///{komga_db}")
    Session = alch.sessionmaker(bind=engine)
    with Session() as session:
        review = session.query(Series).all()
        for series in review:
            try:
                make_korrection(series, yes)
            except ValueError as e:
                if "No first" in str(e) or "Invalid" in str(e):
                    logger.warning("%s Skipping.", e)
                    continue
                logger.debug("%s Skipping.", e)
                continue
        if not dry_run:
            session.commit()
    return "Korrection completed successfully."


def get_comic_info_data(
    root: etree.Element,
    cbz_path: Path,
) -> tuple[etree.Element, etree.Element, str]:
    """Parse a ComicInfo.xml, return the <Series>, <Title> elements and the new title.

    Args:
        root (etree.Element): The root element of the ComicInfo.xml file.
        cbz_path (Path): The path to the cbz file.

    Returns:
        tuple[etree.Element, etree.Element, str]:
            A tuple containing <Series> and <Title> Elements and the new title string.

    Raises:
        ValueError: If ComicInfo.xml is missing necessary information.

    """
    if root.find("Year") is None:
        msg = f"No year found in ComicInfo.xml for {cbz_path}"
        raise ValueError(msg)
    series_elem = root.find("Series")
    title_elem = root.find("Title")
    if title_elem is None:
        msg = f"No title found in ComicInfo.xml for {cbz_path}"
        raise ValueError(msg)
    new_title = f"{series_elem.text} ({root.find('Year').text})"
    if title_elem.text == new_title:
        msg = f"ComicInfo.xml for {cbz_path} is already correct"
        raise ValueError(msg)
    return series_elem, title_elem, new_title


def korrect_comic_info(cbz_path: Path, dry_run: bool = False) -> None:
    """Extract the ComicInfo.xml of a one-shot and alter the title.

    Due to how Komga searches for one-shot series, updating their metadata in the db
    is not sufficient to allow Komga to find them when importing a reading list.
    The solution, instead, is to alter th ComicInfo.xml inside the cbz files to have
    the correct titles. This is done by setting the <Title> element to be
    "Title (YYYY)".

    Args:
        cbz_path (Path): The path to the cbz file.
        dry_run (bool): If True, no changes will be made to the db.

    Raises:
        FileNotFoundError: If the cbz cannot be found, or the cbz has no ComicInfo.xml

    """
    if not cbz_path.exists():
        msg = f"No cbz found for {cbz_path}"
        raise FileNotFoundError(msg)
    # read ComicInfo.xml inside the cbz
    with zipfile.ZipFile(cbz_path, "r") as cbz:
        if "ComicInfo.xml" not in cbz.namelist():
            msg = f"No ComicInfo.xml found in {cbz_path}"
            raise FileNotFoundError(msg)
        # parse the ComicInfo.xml
        with cbz.open("ComicInfo.xml") as xml_file:
            tree = etree.parse(xml_file)
            root = tree.getroot()
        series_elem, title_elem, new_title = get_comic_info_data(root, cbz_path)
        logger.info("ComicInfo: (%s) -> (%s)", series_elem.text, new_title)
        if dry_run:
            return
        title_elem.text = new_title
        cbz_contents = cbz.namelist()
        # create a new XML file in memory
        new_xml = etree.tostring(
            tree,
            pretty_print=True,
            xml_declaration=True,
            encoding="utf-8",
        )
        # create a new cbz in memory
        new_cbz_data = io.BytesIO()
        with zipfile.ZipFile(new_cbz_data, "w") as new_cbz:
            # write all contents of old cbz except ComicInfo
            for item in cbz_contents:
                if item != "ComicInfo.xml":
                    new_cbz.writestr(item, cbz.read(item))
            # write the new ComicInfo
            new_cbz.writestr("ComicInfo.xml", new_xml)
    # write over old cbz with the new cbz that we built in memory
    with cbz_path.open("wb") as new_cbz:
        new_cbz.write(new_cbz_data.getvalue())


def korrect_comic_info_path(
    oneshot_path: str,
    dry_run: bool = False,
) -> None:
    """Read a directory of cbz files, and alter the ComicInfo.xml of each one.

    Args:
        oneshot_path (str): The path to the directory of one-shot cbz files.
        dry_run (bool, optional): If True, no changes will be made to the db.

    """
    cbz_files = pathlib.Path(oneshot_path).rglob("*.cbz")
    for cbz in cbz_files:
        try:
            korrect_comic_info(cbz, dry_run)
        except (ValueError, FileNotFoundError) as e:
            logger.warning("%s", e)
            continue


def korrect_comic_info_database(
    series: Series,
    session: alch.Session,
    dry_run: bool,
    library_prefix: [str, None] = None,
) -> None:
    """Read a series in the komga database, and alter the ComicInfo.xml.

    Args:
        series (Series): The series to make the korrection for.
        session (alch.Session): The session to use to access the database.
        dry_run (bool): If True, no changes will be made to the db.
        library_prefix (str, optional): A comma separated string of path replacements to
            be made to the url of the cbz files.

    """
    if library_prefix:
        old = library_prefix.split(",", maxsplit=1)[0]
        old = r"file://?" + old
        new = library_prefix.split(",")[1]
    else:
        old = r"file://"
        new = ""
    cbz_url = session.query(Book).filter_by(series_id=series.id).first().url
    cbz_path = Path(re.sub(old, new, unquote(cbz_url)))
    korrect_comic_info(cbz_path, dry_run)


def korrect_database_oneshots(
    komga_db: str,
    dry_run: bool = False,
    library_prefix: [str, None] = None,
) -> None:
    """Read a Komga db, and alter the ComicInfo.xml of improperly titled one-shots.

    Args:
        komga_db (str): The path to the Komga database file.
        dry_run (bool, optional): If True, no changes will be made to the db.
        library_prefix (str, optional): comma separated string of path replacements

    """
    engine = create_engine(f"sqlite:///{komga_db}")
    Session = alch.sessionmaker(bind=engine)
    with Session() as session:
        all_series = session.query(Series).filter_by(oneshot=True).all()
        for series in all_series:
            try:
                korrect_comic_info_database(series, session, dry_run, library_prefix)
            except (FileNotFoundError, ValueError) as e:
                if "correct" in str(e):
                    logger.debug("%s Skipping.", e)
                    continue
                logger.warning("%s Skipping.", e)
                continue
