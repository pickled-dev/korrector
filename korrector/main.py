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


def get_release_year(series: Series) -> str:
    """Get the release year for a series.

    If the first issue is available, it will return the release year of that issue.
    If the first issue is not available, it will attempt to guess the year from the
    series name. If no year can be found, it will prompt the user to enter the year
    manually.

    Args:
        series (Series): The series to get the release year for.

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
    response = input(
        f"No first issue found for {series.name}. \
            Enter year manually (Default: {year}): ",
    )
    return response or year


def make_korrection(series: Series) -> None:
    """Alter a series in the komga database to make it easier to import.

    The desired format for the TITLE field in the SERIES_METADTA tablse is:
    "Title (YYYY)"

    Args:
        series (Series): The series to make the korrection for.

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
    title = f"{meta.title} ({get_release_year(series)})"
    # replace single quotes with 2 single quotes to escape single quotes in SQL
    title = title.replace(r"'", r"''")
    logger.info("Korrection: [%s] (%s) -> (%s)", series.name, meta.title, title)
    meta.title = title


def korrect_database(
    komga_db: str,
    backup_path: str = "",
    dry_run: bool = False,
) -> str:
    """Read a Komga db, and alter the names of books in the db.

    Args:
        komga_db (str): The path to the Komga database file.
        backup_path (str, optional): Path where a backup of the db should be stored.
        dry_run (bool, optional): If True, no changes will be made to the db.

    Returns:
        str: A message indicating that the korrection has completed successfully.

    """
    if backup_path:
        backup(komga_db, backup_path)
    engine = create_engine(f"sqlite:///{komga_db}")
    Session = alch.sessionmaker(bind=engine)
    with Session() as session:
        review = session.query(Series).filter_by(oneshot=False).all()
        for series in review:
            try:
                make_korrection(series)
            except ValueError as e:
                if "No first" in str(e) or "Invalid" in str(e):
                    logger.warning("%s Skipping.", e)
                    continue
                logger.debug("%s Skipping.", e)
                continue
        if not dry_run:
            session.commit()
    return "Korrection completed successfully."


def korrect_comic_info(series: Series, session: alch.Session, dry_run: bool) -> None:
    """Extract the ComicInfo.xml of a one-shot and alter the title.

    Due to how Komga searches for one-shot series, updating their metadata in the db
    is not sufficient to allow Komga to find them when importing a reading list.
    The solution, instead, is to alter th ComicInfo.xml inside the cbz files to have
    the correct titles. This is done by setting the <Title> element to be
    "Title (YYYY)".

    Args:
        series (Series): The series to korrect.
        session (alch.Session): The database session.
        dry_run (bool): If True, no changes will be made to the db.

    Raises:
        FileNotFoundError: If the cbz cannot be found, or the cbz has no ComicInfo.xml
        ValueError: If the cbz has no year, or the field is already correct

    """
    cbz_url = session.query(Book).filter_by(series_id=series.id).first().url
    cbz_path = Path(re.sub(r"file://?", "", unquote(cbz_url)))
    if not cbz_path.exists():
        msg = f"No cbz found for {series.name}"
        raise FileNotFoundError(msg)
        # extract ComicInfo.xml to a temporary directory
    with zipfile.ZipFile(cbz_path, "r") as cbz:
        if "ComicInfo.xml" not in cbz.namelist():
            msg = f"No ComicInfo.xml found in {series.name}"
            raise FileNotFoundError(msg)
        # parse the XML
        with cbz.open("ComicInfo.xml") as xml_file:
            tree = etree.parse(xml_file)
            root = tree.getroot()
        if root.find("Year") is None:
            msg = f"No year found in ComicInfo.xml for {series.name}"
            raise ValueError(msg)
        series_elem = root.find("Series")
        title_elem = root.find("Title")
        # if no title field is present, raid ValueError
        if title_elem is None:
            msg = f"No title found in ComicInfo.xml for {series.name}"
            raise ValueError(msg)
        # make the correct title
        new_title = f"{series_elem.text} ({root.find('Year').text})"
        if title_elem.text == new_title:
            msg = f"ComicInfo.xml for {series.name} is already correct"
            raise ValueError(msg)
        logger.info("ComicInfo: (%s) -> (%s)", title_elem.text, new_title)
        if dry_run:
            return
        # set the title
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
            # write new ComicInfo
            new_cbz.writestr("ComicInfo.xml", new_xml)
    # write over old cbz with cbz built in memory
    with cbz_path.open("wb") as cbz:
        cbz.write(new_cbz_data.getvalue())


def korrect_oneshots(komga_db: str, dry_run: bool = False) -> None:
    """Read a Komga db, and alter the ComicInfo.xml of improperly titled one-shots.

    Args:
        komga_db (str): The path to the Komga database file.
        dry_run (bool, optional): If True, no changes will be made to the db.

    """
    engine = create_engine(f"sqlite:///{komga_db}")
    Session = alch.sessionmaker(bind=engine)
    with Session() as session:
        all_series = session.query(Series).filter_by(oneshot=True).all()
        for series in all_series:
            try:
                korrect_comic_info(series, session, dry_run)
            except (FileNotFoundError, ValueError) as e:
                logger.warning("%s Skipping.", e)
                continue
