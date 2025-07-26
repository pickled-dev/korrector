"""Class for accumulated information about an issue from different sources"""
import re
import shutil
import sqlite3
from datetime import datetime
from typing import TypedDict


class Series(TypedDict):
    series_id: str
    name: str
    metadata_title: str
    oneshot: bool
    year: str


def format_sql(sql_cmd: str) -> str:
    """Format a SQL command into a one line string so it can be viewed and copied in debugger.

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
        WHERE id is "{series_id}"
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
        WHERE id is "{series_id}"
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
        WHERE series_id is "{series_id}"
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
        return re.search(r'\((\d{4})\)', series["name"]).group(1)
    sql_cmd = format_sql(
        f'''
        SELECT bm.release_date
        FROM book_metadata bm
        JOIN book b ON bm.book_id = b.id
        JOIN series s ON b.series_id = s.id
        WHERE bm.number = 1 AND s.id = "{series["series_id"]}"
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
    metadata_title = get_metadata_title(series_id, cur)
    try:
        series = get_series(series_id, cur)
    except AttributeError:
        print(f"No year found in the name of {metadata_title}. Skipping.")
        return None
    if series["oneshot"]:
        return make_sql_korrection_oneshot(series)
    # skip series that already have the year in the title
    if metadata_title and "(" in metadata_title and ")" in metadata_title:
        return None
    title = f"{series["metadata_title"]} ({series["year"]})"
    # replace single quotes with 2 single quotes to escape single quotes in SQL
    title = re.sub(r"'", r"''", title)
    print(f"Updating series {series["metadata_title"]} ({series["name"]}) to {title}")
    return format_sql(
        f'''
        UPDATE series_metadata
        SET title = '{title}'
        WHERE series_id is "{series["series_id"]}"
        '''
    )


def make_sql_korrection_oneshot(series: Series) -> str | None:
    pattern = re.compile(r'(.*?)(?: v\d+)? #\d{3}(.*)')
    match = re.match(pattern, series["name"])
    title = match.group(1) + match.group(2)
    print(f"Updating series {series["metadata_title"]} ({series["name"]}) to {title}")
    return format_sql(
        f'''
            UPDATE series_metadata
            SET title = '{title}'
            WHERE series_id is "{series["series_id"]}"
            '''
    )


def korrect_all(komga_db_path: str, komga_backup: str) -> None:
    backup(komga_db_path, komga_backup)
    con = sqlite3.connect(f"{komga_db_path}")
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
        sql_cmd = make_sql_korrection(series_id, cur)
        if sql_cmd is None:
            continue
        cur.execute(sql_cmd)
        con.commit()
