from typing import Final
from unittest.mock import Mock
from korrector import korrector
from korrector.korrector import Series
from tests import test_db

import pytest

TEST_SERIES_ID: Final[str] = "0MDQMN9C47SHT"
TEST_BOOK_ID: Final[str] = "THS74C9NMQDM0"


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
        VALUES ('{TEST_SERIES_ID}', 'Test Series', 1);
        """
    )
    result = korrector.get_oneshot(TEST_SERIES_ID, cur)
    assert result


def test_get_metadata_title():
    con, cur = test_db.make_db()
    cur.executescript(
        f"""
        INSERT INTO SERIES (ID, NAME, oneshot) 
        VALUES ('{TEST_SERIES_ID}', 'Test Series', 0);
        
        INSERT INTO SERIES_METADATA (TITLE, SERIES_ID) 
        VALUES ('Test Metadata Title', '{TEST_SERIES_ID}');
        """
    )
    result = korrector.get_metadata_title(TEST_SERIES_ID, cur)
    assert result == "Test Metadata Title"


def make_series(series_id=TEST_SERIES_ID,
                name="Test Series #000 (1999)",
                title="Test Title (1999)",
                oneshot=False,
                year="1999") -> Series:
    return {
        "series_id": series_id,
        "name": name,
        "metadata_title": title,
        "oneshot": oneshot,
        "year": year
    }


def insert_series(series, cur, number="1", date: str | None = "1999-01-01") -> None:
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
    cur.execute(
        "INSERT INTO BOOK_METADATA (NUMBER, RELEASE_DATE, TITLE, BOOK_ID) VALUES (?, ?, ?, ?)",
        (number, date, series["metadata_title"], TEST_BOOK_ID)
    )


def test_get_release_year_first_issue():
    con, cur = test_db.make_db()
    series = make_series(title="Test Title")
    insert_series(series, cur)
    result = korrector.get_release_year(series, cur)
    assert result == "1999"


def test_get_release_year_no_first_issue(monkeypatch):
    con, cur = test_db.make_db()
    series = make_series(title="Test Title")
    insert_series(series, cur, number="100")
    mock_input = Mock(return_value="")
    monkeypatch.setattr('builtins.input', mock_input)
    result = korrector.get_release_year(series, cur)
    assert result == "1999"
    assert mock_input.called, "Input prompt was not called"
    assert "1999" in mock_input.call_args[0][0]


def test_get_series():
    con, cur = test_db.make_db()
    series = make_series()
    insert_series(series, cur)
    result = korrector.get_series(TEST_SERIES_ID, cur)
    assert result["series_id"] == TEST_SERIES_ID
    assert result["name"] == "Test Series #000 (1999)"
    assert result["metadata_title"] == "Test Title (1999)"
    assert not result["oneshot"]
    assert result["year"] == "1999"


series_cases = [
    # korrected series
    (make_series(), None),
    # untagged series
    (make_series(title="Test Title", year=""), None),
    # normal korrection
    (make_series(title="Test Title"), "Test Title (1999)"),
]


@pytest.mark.parametrize("series, expected", series_cases)
def test_get_korrection(series, expected):
    con, cur = test_db.make_db()
    if series["year"] == "":
        insert_series(series, cur, date=None)
    else:
        insert_series(series, cur)
    result = korrector.make_sql_korrection(series["series_id"], cur)
    expected_sql = korrector.format_sql(
        f"""
        UPDATE series_metadata
        SET title = '{expected}'
        WHERE series_id is "{series["series_id"]}"
        """
    ) if expected else None
    assert result == expected_sql

def test_get_korrection_oneshot():
    con, cur = test_db.make_db()
    series = make_series(name="Test Series v1 #001 (1999)", title="Test Title v1 #001 (1999)", oneshot=True)
    insert_series(series, cur, date=None)
    result = korrector.make_sql_korrection_oneshot(series["series_id"], cur, "")
    expected = korrector.format_sql(
        f"""
        UPDATE series_metadata
        SET title = 'Test Series (1999)'
        WHERE series_id is "{series["series_id"]}"
        """
    )
    assert result == expected


def test_get_korrection_input(monkeypatch):
    con, cur = test_db.make_db()
    series = make_series(title="Test Title")
    insert_series(series, cur, number="100")
    mock_input = Mock(return_value="")
    monkeypatch.setattr('builtins.input', mock_input)
    result = korrector.get_release_year(series, cur)
    assert result == "1999"
    assert mock_input.called, "Input prompt was not called"
    assert "1999" in mock_input.call_args[0][0]