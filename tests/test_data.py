from dataclasses import dataclass
from typing import Final

from korrector.orm import Book, BookMetadata, Series, SeriesMetadata

# Series
TEST_SERIES_ID: Final[str] = "0MDQMN9C47SHT"
TEST_SERIES_NAME: Final[str] = "Test Series v1 (1999)"
ERROR_SERIES_NAME: Final[str] = "Test Series"
# Series Metadata
GOOD_TITLE: Final[str] = "Test Series (1999)"
BAD_TITLE: Final[str] = "Test Series"
TEST_YEAR: Final[str] = "1999"
TEST_DATE: Final[str] = "1999-01-01"
GOOD_COMIC_INFO: Final[str] = "tests/test_assets/KorrectedComicInfo.xml"
# Book
TEST_BOOK_ID: Final[str] = "0MDQMN9C47SHT"

# urls for test cbz
TEST_URL: Final[str] = "file://tests/test_assets/test.cbz"
TEST_CBZ_PATH: Final[str] = "tests/test_assets/test.cbz"
NO_TITLE_URL: Final[str] = "file://tests/test_assets/NoTitleTest.cbz"
NO_DATE_URL: Final[str] = "file://tests/test_assets/NoDateTest.cbz"
NO_COMIC_INFO_URL: Final[str] = "file://tests/test_assets/NoComicInfoTest.cbz"
KORRECTED_COMIC_INFO_URL: Final[str] = (
    "file://tests/test_assets/KorrectedComicInfoTest.cbz"
)

# Book Metadata


def create_test_series(
    series_id: str = TEST_SERIES_ID,
    name: str = TEST_SERIES_NAME,
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
    url: str = TEST_URL,
) -> Book:
    return Book(id=book_id, series_id=series_id, url=url)


def create_test_book_metadata(
    book_id: str = TEST_BOOK_ID,
    number: str = "1",
    release_date: str = TEST_DATE,
) -> BookMetadata:
    return BookMetadata(book_id=book_id, number=number, release_date=release_date)


@dataclass
class SeriesTestCase:
    series: Series
    series_metadata: SeriesMetadata
    book: Book
    book_metadata: BookMetadata


# test_get_release_year_good
GET_RELEASE_YEAR_SUCCESS: Final[dict] = {
    "case": SeriesTestCase(
        create_test_series(),
        create_test_series_metadata(),
        create_test_book(),
        create_test_book_metadata(),
    ),
    "expected": TEST_YEAR,
    "log": "",
}

# test_get_release_year_error
NO_FIRST_ISSUE_NO_YEAR: Final[dict] = {
    "case": SeriesTestCase(
        create_test_series(name=ERROR_SERIES_NAME),
        create_test_series_metadata(),
        create_test_book(),
        create_test_book_metadata(number="100"),
    ),
    "log": f"No first issue, or year, found in {ERROR_SERIES_NAME}",
}
EMPTY_RELEASE_DATE: Final[dict] = {
    "case": SeriesTestCase(
        create_test_series(),
        create_test_series_metadata(),
        create_test_book(),
        create_test_book_metadata(release_date="    "),
    ),
    "log": f"Invalid release date for {TEST_SERIES_NAME}:     ",
}

# test_get_release_year_input
NO_FIRST_ISSUE: Final[dict] = {
    "case": SeriesTestCase(
        create_test_series(),
        create_test_series_metadata(),
        create_test_book(),
        create_test_book_metadata(number="100"),
    ),
    "user_input": None,
    "expected": "1999",
}

# test_make_korrection_success
MAKE_KORRECTION_SUCCESS: Final[dict] = {
    "case": SeriesTestCase(
        create_test_series(),
        create_test_series_metadata(),
        create_test_book(),
        create_test_book_metadata(),
    ),
    "expected": GOOD_TITLE,
    "log": f"({BAD_TITLE}) -> ({GOOD_TITLE})",
}

# test_make_korrection_error
ALREADY_CORRECT: Final[dict] = {
    "case": SeriesTestCase(
        create_test_series(),
        create_test_series_metadata(title=GOOD_TITLE),
        create_test_book(),
        create_test_book_metadata(),
    ),
    "log": f"{TEST_SERIES_NAME} is already correct [{GOOD_TITLE}]",
}
MANUAL_LOCK: Final[dict] = {
    "case": SeriesTestCase(
        create_test_series(),
        create_test_series_metadata(title_lock=True),
        create_test_book(),
        create_test_book_metadata(),
    ),
    "log": f"{TEST_SERIES_NAME} is manually locked by user.",
}

# test korrect_comic_info_success
NORMAL_COMIC_INFO: Final[dict] = {
    "path": TEST_CBZ_PATH,
    "expected": GOOD_COMIC_INFO,
}
