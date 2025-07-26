import sqlite3
from typing import Tuple

"""
test_db.py

Provides helper functions to set up an in-memory SQLite database
with the minimal schema and tables needed to run tests on the Komga
database-related functions.

Functions:
- make_db(): Creates the in-memory DB and tables, returns connection and cursor.

Note:
SQL commands are copy/pasted from `.schema {table}` commands in a real Komga database.
"""


def create_series_table(cur: sqlite3.Cursor) -> None:
    cur.executescript(
        """
        CREATE TABLE SERIES (
          ID VARCHAR NOT NULL PRIMARY KEY,
          NAME VARCHAR NOT NULL,
          oneshot boolean NOT NULL DEFAULT 0
        );
        """)


def create_series_metadata_table(cur: sqlite3.Cursor) -> None:
    cur.executescript(
        """
        CREATE TABLE SERIES_METADATA (
          TITLE VARCHAR NOT NULL,
          SERIES_ID VARCHAR NOT NULL PRIMARY KEY
        );
        """)


def create_book_table(cur: sqlite3.Cursor) -> None:
    cur.executescript(
        """
        CREATE TABLE BOOK (
            ID                 varchar  NOT NULL PRIMARY KEY,
            URL                varchar  NOT NULL,
            SERIES_ID          varchar  NOT NULL
        );
        """)


def create_book_metadata_table(cur: sqlite3.Cursor) -> None:
    cur.executescript(
        """
        CREATE TABLE BOOK_METADATA
        (
            NUMBER             varchar  NOT NULL,
            RELEASE_DATE       date     NULL,
            TITLE              varchar  NOT NULL,
            BOOK_ID            varchar  NOT NULL PRIMARY KEY
        );
        """)


def make_db() -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
    con = sqlite3.connect(":memory:")
    cur = con.cursor()

    create_series_table(cur)
    create_series_metadata_table(cur)
    create_book_table(cur)
    create_book_metadata_table(cur)

    con.commit()
    return con, cur