import io
import logging
import re
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from typing import TypedDict
from urllib.parse import unquote

from lxml import etree


class Series(TypedDict):
    series_id: str
    name: str
    metadata_title: str
    oneshot: bool
    year: str


logger = logging.getLogger(__name__)


def format_sql(sql_cmd: str) -> str:
    """Format SQL command into a one-line string so it can be viewed and copied in a debugger.

    Replaces all consecutive whitespace characters with a single space, and
    removes any leading or trailing whitespace.

    Args:
        sql_cmd: The SQL command string to format.
    Returns:
        A formatted string.
    """
    return " ".join(sql_cmd.split())


def backup(komga_db_path: str, komga_backup: str) -> None:
    """Backup the Komga database to a specified backup path.

    Args:
        komga_db_path (str): The path to the Komga database.
        komga_backup (str): The path where the backup should be stored.
    """
    backup_name = f"{datetime.now().strftime("%Y-%m-%d(%H_%M_%S)")}.sqlite"
    src = f"{komga_db_path}"
    dest = f"{komga_backup}/{backup_name}"
    shutil.copy(src, dest)


def get_name(series_id: str, cur: sqlite3.Cursor) -> str:
    """Retrieve the name of a series given its id.

    Args:
        series_id (str): The id of the series to retrieve.
        cur (sqlite3.Cursor): The database cursor to use for queries.
    Returns:
        str: The name of the series.
    """
    sql_cmd = format_sql(
        f'''
        SELECT name
        FROM series
        WHERE id is '{series_id}'
        '''
    )
    return cur.execute(sql_cmd).fetchone()[0]


def get_oneshot(series_id: str, cur: sqlite3.Cursor) -> bool:
    """Retrieve whether a series is an oneshot given its id.

    Args:
        series_id (str): The id of the series to retrieve.
        cur (sqlite3.Cursor): The database cursor to use for queries.
    Returns:
        bool: True if the series is an oneshot, False otherwise.
    """
    sql_cmd = format_sql(
        f'''
        SELECT oneshot
        FROM series
        WHERE id is '{series_id}'
        '''
    )
    return cur.execute(sql_cmd).fetchone()[0]


def get_metadata_title(series_id: str, cur: sqlite3.Cursor) -> str:
    """Retrieve the metadata title of a series given its id.

    Args:
        series_id (str): The id of the series to retrieve.
        cur (sqlite3.Cursor): The database cursor to use for queries.
    Returns:
        str: The metadata title of the series.
    """
    sql_cmd = format_sql(
        f'''
        SELECT TITLE
        FROM series_metadata
        WHERE series_id is '{series_id}'
        '''
    )
    return cur.execute(sql_cmd).fetchone()[0]


def get_release_year(series: Series, cur: sqlite3.Cursor) -> str:
    """Retrieve the release year for a series.

    If the series is an oneshot, extracts the year from the series name.
    Otherwise, attempts to get the release year from the first issue's metadata.
    If no first issue is found, guesses the year from the series name and prompts the user for manual input.

    Args:
        series (Series): The series information dictionary.
        cur (sqlite3.Cursor): The database cursor to use for queries.

    Returns:
        str: The release year as a string.
    """
    if series["oneshot"]:
        match = re.search(r'\((\d{4})\)', series["name"])
        if not match:
            raise ValueError(f"No year found in name of {series['name']}.")
        return match.group(1)
    sql_cmd = format_sql(
        f'''
        SELECT bm.release_date
        FROM book_metadata bm
        JOIN book b ON bm.book_id = b.id
        JOIN series s ON b.series_id = s.id
        WHERE bm.number = '1' AND s.id = '{series["series_id"]}'
        '''
    )
    # TypeError is raised if no issue is numbered 1 in the series
    try:
        release_date = cur.execute(sql_cmd).fetchone()[0]
    except TypeError:
        # Guess the year from the series name if no first issue is found
        name = get_name(series["series_id"], cur)
        match = re.search(r'\((\d{4})\)', name)
        year = match.group(1)
        response = input(
            f"No first issue found for {series["metadata_title"]}. Enter year manually (Default is {year}): "
        )
        return response if response else year
    return release_date.split('-')[0]


def get_series(series_id: str, cur: sqlite3.Cursor) -> Series:
    """Construct a Series dictionary with information about a series.

    Args:
        series_id (str): The id of the series to retrieve.
        cur (sqlite3.Cursor): The database cursor to use for queries.

    Returns:
        Series: A dictionary containing series_id, name, metadata_title, oneshot, and year.
    """
    s: Series = {
        "series_id": series_id,
        "name": get_name(series_id, cur),
        "metadata_title": get_metadata_title(series_id, cur),
        "oneshot": get_oneshot(series_id, cur),
        "year": "",
    }
    s["year"] = get_release_year(s, cur)
    return s


def make_sql_korrection(series_id: str, cur: sqlite3.Cursor) -> str | None:
    """Generate an SQL update statement to correct the title of a series by appending the release year.

    Skips series that already have the year in the title. If the year cannot be determined, the function
    logs a message and returns None.

    Args:
        series_id (str): The id of the series to update.
        cur (sqlite3.Cursor): The database cursor to use for queries.

    Returns:
        str | None: The SQL update statement if a correction is needed, otherwise None.
    """
    try:
        series = get_series(series_id, cur)
    except AttributeError:
        logger.debug(f"No year found in the name of {get_name(series_id, cur)}. Skipping.")
        return None
    title = f"{series["metadata_title"]} ({series["year"]})"
    # replace single quotes with 2 single quotes to escape single quotes in SQL
    title = re.sub(r"'", r"''", title)
    logger.debug(f"[{series["name"]}]")
    logger.info(f"({series["metadata_title"]}) -> ({title})")
    return format_sql(
        f'''
        UPDATE series_metadata
        SET title = '{title}'
        WHERE series_id is "{series["series_id"]}"
        '''
    )


def get_url(series_id: str, cur: sqlite3.Cursor) -> str:
    """Retrieve the URL of a series given its id.

    Args:
        series_id (str): The id of the series to retrieve.
        cur (sqlite3.Cursor): The database cursor to use for queries.
    Returns:
        str: The URL of the series.
    """
    sql_cmd = format_sql(
        f'''
        SELECT b.url
        FROM book b
        JOIN series s ON b.series_id=s.id
        WHERE series_id is '{series_id}'
        '''
    )
    return cur.execute(sql_cmd).fetchone()[0]


def korrect_comic_info(series_id: str, cur: sqlite3.Cursor, komga_prefix: str, dry_run: bool):
    series_path = get_url(series_id, cur)
    # FIXME: this regex will mean this only works with my specific docker/directory setup
    path = re.sub(r'file://?data', "", unquote(series_path))
    path = Path(komga_prefix + path)
    # extract ComicInfo.xml to a temporary directory
    if not path.exists():
        logger.info(f"\033[91m{get_name(series_id, cur)} cannot be found at {str(path)}\033[0m")
        return
    with zipfile.ZipFile(path, 'r') as cbz:
        if "ComicInfo.xml" not in cbz.namelist():
            logger.info(f"\033[91m{get_name(series_id, cur)} does not have a ComicInfo.xml \033[0m")
            return
        with cbz.open("ComicInfo.xml") as xml_file:
            tree = etree.parse(xml_file)
            root = tree.getroot()
        series_elem = root.find("Series")
        title_elem = root.find("Title")
        if title_elem is None:
            title_elem = etree.Element("Title")
            title_elem.text = series_elem.text
            root.append(title_elem)
            logger.info(f"Creating title field: {title_elem.text}")
        elif title_elem.text == series_elem.text:
            return
        else:
            logger.info(f"ComicInfo.xml: {title_elem.text} -> {series_elem.text}")
        if dry_run:
            return
        title_elem.text = series_elem.text
        cbz_contents = cbz.namelist()
        # create a new XML file in memory
        new_xml = etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding="utf-8")
        # create a new cbz in memory
        new_cbz_data = io.BytesIO()
        with zipfile.ZipFile(new_cbz_data, "w") as new_cbz:
            # write all contents of old cbz except ComicInfo
            for item in cbz_contents:
                if item != "ComicInfo.xml":
                    new_cbz.writestr(item, cbz.read(item))
            # write new ComicInfo
            new_cbz.writestr("ComicInfo.xml", new_xml)
    logger.debug(f"Writing new CBZ")
    # write over old cbz with cbz built in memory
    with open(path, "wb") as cbz:
        cbz.write(new_cbz_data.getvalue())


def get_locked(series_id: str, cur: sqlite3.Cursor) -> bool:
    """get the TITLE_LOCK field of a series

    when a user manually edits the metadata_title of a series in the komga web interface,
    it is marked as locked in the SERIES_METADATA table to prevent automatic corrections.
    0 is not locked, 1 is locked.

    Args:
        series_id (str): The id of the series to check.
        cur (sqlite3.Cursor): The database cursor to use for queries.
    Returns:
        bool: True if the series is locked, False otherwise.
    """
    sql_cmd = format_sql(
        f'''
        SELECT title_lock
        FROM series_metadata
        WHERE series_id is '{series_id}'
        '''
    )
    return cur.execute(sql_cmd).fetchone()[0]


def korrect_all(komga_db: str, backup_path="", komga_prefix="", dry_run=False) -> str:
    """Perform a batch correction of series titles in the Komga database.

    This function creates a backup of the Komga database, connects to it, and iterates over all series.
    For each series, it determines if it is a oneshot or not, generates the appropriate SQL correction
    statement, and updates the series title in the database if needed.

    Args:
        komga_db (str): Path to the Komga database file.
        backup_path (str, optional): Directory where the database backup will be stored.
        komga_prefix (str, optional): Prefix to use for file paths when extracting ComicInfo.xml. Defaults to "".
        dry_run (bool, optional): If True, performs a dry run without making changes. Defaults to False.

    Returns:
        None
    """
    if backup_path:
        backup(komga_db, backup_path)
    con = sqlite3.connect(f"{komga_db}", timeout=10)
    cur = con.cursor()
    sql_cmd = format_sql(
        """
        SELECT id
        FROM series
        """
    )
    series_ids = cur.execute(sql_cmd).fetchall()
    for series_id in series_ids:
        series_id = series_id[0]
        if get_oneshot(series_id, cur):
            korrect_comic_info(series_id, cur, komga_prefix, dry_run)
            continue
        else:
            metadata_title = get_metadata_title(series_id, cur)
            # skip series that already have the year in the title
            if metadata_title and "(" in metadata_title and ")" in metadata_title:
                logger.debug(f"{get_name(series_id, cur)} is already correct [{metadata_title}")
                continue
            sql_cmd = make_sql_korrection(series_id, cur)
        if sql_cmd is None:
            continue
        if not dry_run: cur.execute(sql_cmd)
    if not dry_run:
        con.commit()
    return "Korrection completed successfully."
