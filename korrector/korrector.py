"""Class for accumulated information about an issue from different sources"""
import glob
import os
import re
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime

import untangle


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


def update_oneshots(oneshot_path: str):
    """Update one-shots from a given directory.

    Iterate through all cbz files in the given directory and its subdirectories.
    For each cbz file, extract the "ComicInfo.xml" file and copy the "Series" field
    to the "Title" field, or create a new "Title" field if it doesn't exist.

    Args:
        oneshot_path: The path to the directory containing the one-shot cbz files.
    Returns:
        None
    """
    # Iterate recursively through One-Shots directory (see https://komga.org/docs/guides/oneshots/)
    for cbz_file in glob.iglob(oneshot_path + "/**/*.cbz", recursive=True):
        # get komga.series_title (story_title) and metron.series_id from ComicInfo.xml
        with zipfile.ZipFile(cbz_file, "r") as zip_:
            try:
                zip_.extract("ComicInfo.xml")
            except KeyError:
                continue
        untangled = untangle.parse("ComicInfo.xml").ComicInfo
        if "MetronTagger" in untangled.Notes.cdata:
            try:
                with open(
                        "ComicInfo.xml", "r", encoding="utf-8", errors="replace"
                ) as f:
                    contents = f.read()
                    encode = "utf-8"
            except UnicodeDecodeError:
                with open(
                        "ComicInfo.xml", "r", encoding="latin-1", errors="replace"
                ) as f:
                    contents = f.read()
                    encode = "latin-1"
            story_title = ""
            series_name = ""
            for line in contents.split("\n"):
                if "<Series>" in line:
                    series_name = line.split(">")[1].split("<")[0]
                if "<Title>" in line:
                    story_title = line.split(">")[1].split("<")[0]
            if story_title == series_name:
                continue
            print(f"Updating {cbz_file}")
            # write metron.series_title to Title field in ComicInfo.xml
            if story_title and series_name:
                contents = contents.replace(story_title, series_name)
            # or add title field with metron.series_title
            if series_name and not story_title:
                series_tag = f"<Series>{series_name}</Series>"
                i = contents.index(series_tag)
                contents = contents[:i] + f"<Title>{series_name}</Title>" + contents[i:]
            # replace old ComicInfo.xml with new one
            with open("ComicInfo.xml", "w", encoding=encode) as f:
                f.write(contents)
            tmpfd, tmpname = tempfile.mkstemp(dir=os.path.dirname(cbz_file))
            os.close(tmpfd)
            # rebuild cbz
            info_name = "ComicInfo.xml"
            with zipfile.ZipFile(cbz_file, "r") as zipin:
                with zipfile.ZipFile(tmpname, "w") as zipout:
                    zipout.comment = zipin.comment
                    for item in zipin.infolist():
                        if item.filename != info_name:
                            zipout.writestr(item, zipin.read(item.filename))
            # replace old zip with new one
            os.remove(cbz_file)
            os.rename(tmpname, cbz_file)
            # add new contents
            with zipfile.ZipFile(
                    cbz_file, "a", compression=zipfile.ZIP_DEFLATED
            ) as zip_:
                zip_.writestr("ComicInfo.xml", contents)
            print("done.")
        # remove old contents
        os.remove("ComicInfo.xml")


def update_komga_series(komga_config_path: str) -> None:
    """update the komga database's series metadata to be compatible with DieselTech reading lists

    When you try to add a reading list to komga, it will check the 'title' field in the
    'SERIES_METADATA table for a name of the format 'series_name (year_began)'. But, for whatever
    reason, this is not how komga initially stores the series metadata. This function updates the
    'title' field so that komga will properly match issues with when given a DieselTech reading
    list. Will not work with series located in the oneshots folder as Komga uses the
    COMIC_METADATA table to match reading lists for oneshots.

    Args:
        komga_config_path: path to komga database
    """

    con = sqlite3.connect(f"{komga_config_path}\\database.sqlite")
    cur = con.cursor()
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
    # update titles
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
    print("done.")


def update_komga_series_oneshots(oneshot_path: str, komga_config_path: str) -> None:
    """Update the title field in the Komga database for oneshot books.

    This function updates the title of each oneshot book in the Komga database
    to include the release year in the format 'title (year)'. It retrieves the
    list of CBZ files from the specified oneshot directory, constructs URLs
    for each file, and matches them to the corresponding book entries in the
    Komga database. If the title does not already include the year, it appends
    the release year to the title.

    Args:
        oneshot_path (str): Path to the directory containing oneshot CBZ files.
        komga_config_path (str): Path to the Komga database configuration.

    Returns:
        None
    """

    con = sqlite3.connect(f"{komga_config_path}\\database.sqlite")
    cur = con.cursor()
    files = [
        f"file:/data{y}"
        for x in os.walk(oneshot_path)
        for y in glob.glob(os.path.join(x[0], "*.cbz"))
    ]
    urls = []
    for file in files:
        url = re.sub(r"Z:\\print", r"", file)
        url = re.sub(r"\\", r"/", url)
        url = re.sub(r"print/", r"", url)
        url = re.sub(r" ", r"%20", url)
        url = re.sub(r"#", r"%23", url)
        url = re.sub(r"ñ", r"%C3%B1", url)

        urls.append(url)
    ids = []
    for url in urls:
        sql_cmd = format_sql(
            f'''
            SELECT id
            FROM  BOOK
            WHERE url is "{url}"
            '''
        )
        _id = cur.execute(sql_cmd).fetchone()[0]
        ids.append(_id)
    for id_ in ids:
        sql_cmd = format_sql(
            f'''
            SELECT title
            FROM book_metadata 
            WHERE book_id is "{id_}"
            '''
        )
        old_title = cur.execute(sql_cmd).fetchone()[0]
        if "(" in old_title and ")" in old_title:
            continue
        sql_cmd = format_sql(
            f'''
            SELECT release_date
            FROM book_metadata
            WHERE book_id is "{id_}"
            '''
        )
        year = int(cur.execute(sql_cmd).fetchone()[0][:4])
        new_title = f"{old_title} ({year})"
        sql_cmd = format_sql(
            f'''
            UPDATE book_metadata
            SET title = "{new_title}"
            WHERE book_id is "{id_}"
            '''
        )
        cur.execute(sql_cmd)
    con.commit()


def update_komga(
        oneshot_path: str, komga_config_path: str, komga_backup_path: str
) -> None:
    """Backs up the current Komga db and updates the series titles

    Args:
        oneshot_path (str): The path to the oneshots folder.
        komga_config_path (str): The path to the Komga configuration folder.
        komga_backup_path (str):
            The path to the folder where backups of the Komga configuration should be stored.
    """
    update_oneshots(oneshot_path)
    backup_name = datetime.now().strftime("%Y-%m-%d(%H_%M_%S)")
    src = f"{komga_config_path}\\"
    dest = f"{komga_backup_path}\\{backup_name}\\"
    shutil.copytree(src, dest)
    update_komga_series(komga_config_path)
    # update_komga_series_oneshots(oneshot_path, komga_config_path)
