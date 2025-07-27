import re
from typing import Final
from unittest.mock import Mock
from korrector import korrector
from korrector.korrector import Series
from tests import test_db

import pytest

TEST_SERIES_ID: Final[str] = "0MDQMN9C47SHT"
TEST_BOOK_ID: Final[str] = "THS74C9NMQDM0"
TEST_NAME: Final[str] = "Test Series #000 (1999)"
TEST_TITLE: Final[str] = "Test Series (1999)"
TEST_YEAR: Final[str] = "1999"
TEST_DATE: Final[str] = "1999-01-01"


def test_get_name():
    con, cur = test_db.make_db()
    cur.executescript(
        f"""
        INSERT INTO SERIES (ID, NAME, oneshot) 
        VALUES ('{TEST_SERIES_ID}', 'Test Series', 0);
        """
    )
    result = korrector.get_name(TEST_SERIES_ID, cur)
    assert result == "Test Series"


def test_get_oneshot():
    con, cur = test_db.make_db()
    cur.executescript(
        f"""
        INSERT INTO SERIES (ID, NAME, oneshot) 
        VALUES ('{TEST_SERIES_ID}', '{TEST_NAME}', 1);
        """
    )
    result = korrector.get_oneshot(TEST_SERIES_ID, cur)
    assert result


def test_get_metadata_title():
    con, cur = test_db.make_db()
    cur.executescript(
        f"""
        INSERT INTO SERIES (ID, NAME, oneshot) 
        VALUES ('{TEST_SERIES_ID}', '{TEST_NAME}', 0);
        
        INSERT INTO SERIES_METADATA (TITLE, SERIES_ID) 
        VALUES ('{TEST_TITLE}', '{TEST_SERIES_ID}');
        """
    )
    result = korrector.get_metadata_title(TEST_SERIES_ID, cur)
    assert result == TEST_TITLE


def make_series(series_id=TEST_SERIES_ID,
                name=TEST_NAME,
                title=TEST_TITLE,
                oneshot=False,
                year=TEST_YEAR,
                locked=False) -> Series:
    return {
        "series_id": series_id,
        "name": name,
        "metadata_title": title,
        "oneshot": oneshot,
        "year": year,
        "locked": locked
    }


def insert_series(series, cur, number="1", date: str | None = TEST_DATE) -> None:
    cur.execute(
        "INSERT INTO SERIES (ID, NAME, oneshot) VALUES (?, ?, ?)",
        (series["series_id"], series["name"], series["oneshot"])
    )
    cur.execute(
        "INSERT INTO SERIES_METADATA (TITLE, TITLE_LOCK, SERIES_ID) VALUES (?, ?, ?)",
        (series["metadata_title"], False, series["series_id"])
    )
    cur.execute(
        "INSERT INTO BOOK (ID, URL, SERIES_ID) VALUES (?, ?, ?)",
        (TEST_BOOK_ID, "file://test_assets/test.cbz", series["series_id"])
    )
    if series["year"] == "": date = None
    cur.execute(
        "INSERT INTO BOOK_METADATA (NUMBER, RELEASE_DATE, TITLE, BOOK_ID) VALUES (?, ?, ?, ?)",
        (number, date, series["metadata_title"], TEST_BOOK_ID)
    )


def test_get_release_year_first_issue():
    con, cur = test_db.make_db()
    series = make_series(title="Test Title")
    insert_series(series, cur)
    result = korrector.get_release_year(series, cur)
    assert result == TEST_YEAR


def test_get_release_year_no_first_issue(monkeypatch):
    con, cur = test_db.make_db()
    series = make_series(title="Test Title")
    insert_series(series, cur, number="100")
    mock_input = Mock(return_value="")
    monkeypatch.setattr('builtins.input', mock_input)
    result = korrector.get_release_year(series, cur)
    assert result == TEST_YEAR
    assert mock_input.called, "Input prompt was not called"
    assert TEST_YEAR in mock_input.call_args[0][0]


def test_get_series_good():
    con, cur = test_db.make_db()
    series = make_series()
    insert_series(series, cur)
    result = korrector.get_series(TEST_SERIES_ID, cur)
    assert result["series_id"] == TEST_SERIES_ID
    assert result["name"] == TEST_NAME
    assert result["metadata_title"] == TEST_TITLE
    assert result["oneshot"] == False
    assert result["year"] == TEST_YEAR
    assert result["locked"] == False


get_series_error_cases = [
    # untagged series
    (make_series(name="Test Name", year=""), f"No year found in the name of {TEST_SERIES_ID}")
]


@pytest.mark.parametrize("series, expected", get_series_error_cases)
def test_get_series_error(series, expected):
    con, cur = test_db.make_db()
    insert_series(series, cur)
    with pytest.raises(ValueError, match=expected):
        korrector.get_series(series["series_id"], cur)


series_good_cases = [
    # normal korrection
    (make_series(title="Test Series"), TEST_TITLE),
]


@pytest.mark.parametrize("series, expected", series_good_cases)
def test_get_korrection(series, expected):
    con, cur = test_db.make_db()
    insert_series(series, cur)
    result = korrector.get_sql_korrection(series)
    expected_sql = korrector.format_sql(
        f"""
        UPDATE series_metadata
        SET title = '{expected}'
        WHERE series_id is "{series["series_id"]}"
        """
    )
    assert result == expected_sql


series_error_cases = [
    # already korrect series
    (make_series(), f"{TEST_NAME} is already correct [{TEST_TITLE}]"),
]


@pytest.mark.parametrize("series, expected", series_error_cases)
def test_get_korrection_error(series, expected):
    con, cur = test_db.make_db()
    insert_series(series, cur)
    with pytest.raises(ValueError, match=re.escape(expected)):
        korrector.get_sql_korrection(series)


def test_get_korrection_input(monkeypatch):
    con, cur = test_db.make_db()
    series = make_series(title="Test Title")
    insert_series(series, cur, number="100")
    mock_input = Mock(return_value="")
    monkeypatch.setattr('builtins.input', mock_input)
    result = korrector.get_release_year(series, cur)
    assert result == TEST_YEAR
    assert mock_input.called, "Input prompt was not called"
    assert TEST_YEAR in mock_input.call_args[0][0]
