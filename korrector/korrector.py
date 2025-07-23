"""Class for accumulated information about an issue from different sources"""
import re
import shutil
import sqlite3
from datetime import datetime
from typing import TypedDict


class Series(TypedDict):
    id: str
    name: str
    year: str
    oneshot: bool


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


def korrect(komga_db_path: str, komga_backup: str) -> None:
    backup(komga_db_path, komga_backup)
    con = sqlite3.connect(f"{komga_db_path}")
    cur = con.cursor()
    series = get_series(cur)
    for s in series:
        sql_cmd = format_sql(
            f'''
            SELECT title
            FROM series_metadata
            WHERE series_id is "{s["id"]}"
            '''
        )
        old_title = cur.execute(sql_cmd).fetchone()[0]
        # skip any series that has '()', those are already updated
        if "(" in old_title and ")" in old_title:
            continue
        title = f"{old_title} ({s["year"]})"
        title = re.sub(r"'", r"''", title)
        sql_cmd = format_sql(
            f'''
            UPDATE series_metadata
            SET title = '{title}'
            WHERE series_id is "{s["id"]}"
            '''
        )
        cur.execute(sql_cmd)
    con.commit()


def backup(komga_db_path: str, komga_backup: str) -> None:
    """Backup the Komga database to a specified backup path.

    Args:
        komga_db_path (str): The path to the Komga database.
        komga_backup (str): The path where the backup should be stored.
    """
    backup_name = datetime.now().strftime("%Y-%m-%d(%H_%M_%S)")
    src = f"{komga_db_path}"
    dest = f"{komga_backup}\\{backup_name}\\"
    shutil.copytree(src, dest)


def get_series(cur: sqlite3.Cursor) -> list[Series]:
    """Retrieve all series from the database with their id, name, and start year.

    This function queries the `series` table to get all series ids and names,
    then determines the earliest release year for each series by examining the
    `release_date` field in the `book_metadata` table for all books in the series.
    If there isn't a first issue for a series, it will skip that series and log a warning.

    Args:
        cur (sqlite3.Cursor): The database cursor to use for queries.

    Returns:
        list[Series]: A list of dictionaries, each containing the id, name, year, and oneshot of a series.
    """
    # store all series ids in series_id
    sql_cmd = format_sql(
        """
        SELECT id
        FROM series
        """
    )
    series_ids = cur.execute(sql_cmd).fetchall()
    series = []
    # map series names to ids
    for id_ in series_ids:
        id_ = id_[0]
        sql_cmd = format_sql(
            f'''
            SELECT name
            FROM series
            WHERE id is "{id_}"
            '''
        )
        series_name = cur.execute(sql_cmd).fetchone()[0]
        series.append({"id": id_, "name": series_name})
    # TODO: if a book doesn't have a first issue, the function should skip it and log a warning
    # get start years for each series
    for s in series:
        # get every book from each series
        sql_cmd = format_sql(
            f'''
            SELECT id
            FROM book
            WHERE series_id is "{s["id"]}"
            '''
        )
        book_ids = cur.execute(sql_cmd).fetchall()
        # get release year for series
        release_years = []
        for book_id in book_ids:
            sql_cmd = format_sql(
                f'''
                SELECT release_date
                FROM book_metadata
                WHERE book_id is "{book_id[0]}"
                '''
            )
            release_date = cur.execute(sql_cmd).fetchone()[0]
            if release_date:
                release_years.append(int(release_date[:4]))
        s["year"] = min(release_years)
        # get oneshot status for series
        sql_cmd = format_sql(
            f'''
            SELECT oneshot
            FROM series
            WHERE id is "{s["id"]}"
            '''
        )
        oneshot = cur.execute(sql_cmd).fetchone()[0]
        s["oneshot"] = oneshot
    return series
