from typing import Final

from korrector.orm import Book, BookMetadata, Series, SeriesMetadata

TEST_SERIES_ID: Final[str] = "0MDQMN9C47SHT"
TEST_BOOK_ID: Final[str] = "THS74C9NMQDM0"
GOOD_NAME: Final[str] = "Test Series v1 (1999)"
BAD_NAME: Final[str] = "Test Series"
GOOD_TITLE: Final[str] = "Test Series (1999)"
BAD_TITLE: Final[str] = "Test Series"
TEST_YEAR: Final[str] = "1999"
TEST_DATE: Final[str] = "1999-01-01"
GOOD_URL: Final[str] = "file://tests/test_assets/test.cbz"
BAD_URL: Final[str] = "file://tests/test_assets/does_not_exist.cbz"
BAD_URL_FILTERED: Final[str] = "tests/test_assets/does_not_exist.cbz"
BAD_COMIC_INFO: Final[str] = "tests/test_assets/KorrectedComicInfo.xml"
GOOD_COMIC_INFO: Final[str] = "tests/test_assets/KorrectedComicInfo.xml"


def create_test_series(
    series_id: str = TEST_SERIES_ID,
    name: str = GOOD_NAME,
    oneshot: int = 0,
) -> Series:
    return Series(id=series_id, name=name, oneshot=oneshot)


def create_test_series_metadata(
    series_id: str = TEST_SERIES_ID,
    title: str = BAD_TITLE,
    title_lock: int = 0,
) -> SeriesMetadata:
    return SeriesMetadata(series_id=series_id, title=title, title_lock=title_lock)


def create_test_book(
    book_id: str = TEST_BOOK_ID,
    series_id: str = TEST_SERIES_ID,
    url: str = GOOD_URL,
) -> Book:
    return Book(id=book_id, series_id=series_id, url=url)


def create_test_book_metadata(
    book_id: str = TEST_BOOK_ID,
    number: str = "1",
    release_date: str = TEST_DATE,
) -> BookMetadata:
    return BookMetadata(book_id=book_id, number=number, release_date=release_date)


# test_get_release_year_good
VALID_SERIES: Final[dict] = {
    "case": {
        "series": create_test_series(),
        "series_metadata": create_test_series_metadata(),
        "book": create_test_book(),
        "book_metadata": create_test_book_metadata(),
    },
    "expected": TEST_YEAR,
    "log": "",
}

# test_get_release_year_error
NO_FIRST_ISSUE_NO_YEAR: Final[dict] = {
    "case": {
        "series": create_test_series(name=BAD_NAME),
        "series_metadata": create_test_series_metadata(),
        "book": create_test_book(),
        "book_metadata": create_test_book_metadata(number="100"),
    },
    "log": f"No first issue, or year, found in {BAD_NAME}",
}
EMPTY_RELEASE_DATE: Final[dict] = {
    "case": {
        "series": create_test_series(),
        "series_metadata": create_test_series_metadata(),
        "book": create_test_book(),
        "book_metadata": create_test_book_metadata(release_date="    "),
    },
    "log": f"Invalid release date for {GOOD_NAME}:     ",
}

# test_get_release_year_input
NO_FIRST_ISSUE: Final[dict] = {
    "case": {
        "series": create_test_series(),
        "series_metadata": create_test_series_metadata(),
        "book": create_test_book(),
        "book_metadata": create_test_book_metadata(number="100"),
    },
    "user_input": None,
    "expected": "1999",
}

# test_make_korrection_good
STANDARD_KORRECTION: Final[dict] = {
    "case": {
        "series": create_test_series(),
        "series_metadata": create_test_series_metadata(),
        "book": create_test_book(),
        "book_metadata": create_test_book_metadata(),
    },
    "expected": GOOD_TITLE,
    "log": f"({BAD_TITLE}) -> ({GOOD_TITLE})",
}

# test_make_korrection_error
ALREADY_CORRECT: Final[dict] = {
    "case": {
        "series": create_test_series(),
        "series_metadata": create_test_series_metadata(title=GOOD_TITLE),
        "book": create_test_book(),
        "book_metadata": create_test_book_metadata(),
    },
    "log": f"{GOOD_NAME} is already correct [{GOOD_TITLE}]",
}
MANUAL_LOCK: Final[dict] = {
    "case": {
        "series": create_test_series(),
        "series_metadata": create_test_series_metadata(title_lock=True),
        "book": create_test_book(),
        "book_metadata": create_test_book_metadata(),
    },
    "log": f"{GOOD_NAME} is manually locked by user.",
}

# test_korrect_comic_info_good
NORMAL_COMIC_INFO: Final[dict] = {
    "case": {
        "series": create_test_series(),
        "series_metadata": create_test_series_metadata(),
        "book": create_test_book(),
        "book_metadata": create_test_book_metadata(),
    },
    "expected": GOOD_COMIC_INFO,
}

# test_korrect_comic_info_error
BAD_PATH_COMIC_INFO: Final[dict] = {
    "case": {
        "series": create_test_series(),
        "series_metadata": create_test_series_metadata(),
        "book": create_test_book(url=BAD_URL),
        "book_metadata": create_test_book_metadata(),
    },
    "expected": f"{GOOD_NAME} cannot be found at {BAD_URL_FILTERED}",
}
