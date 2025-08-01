from dataclasses import dataclass
from typing import Final

import tests.test_constants as tc
from korrector.orm import Book, BookMetadata, Series, SeriesMetadata


def create_test_series(
    series_id: str = tc.TEST_SERIES_ID,
    name: str = tc.TEST_SERIES_NAME,
    oneshot: int = 0,
) -> Series:
    return Series(id=series_id, name=name, oneshot=oneshot)


def create_test_series_metadata(
    series_id: str = tc.TEST_SERIES_ID,
    title: str = tc.BAD_TITLE,
    title_lock: int = 0,
) -> SeriesMetadata:
    return SeriesMetadata(series_id=series_id, title=title, title_lock=title_lock)


def create_test_book(
    book_id: str = tc.TEST_BOOK_ID,
    series_id: str = tc.TEST_SERIES_ID,
    url: str = tc.TEST_URL,
) -> Book:
    return Book(id=book_id, series_id=series_id, url=url)


def create_test_book_metadata(
    book_id: str = tc.TEST_BOOK_ID,
    number: str = "1",
    release_date: str = tc.TEST_DATE,
) -> BookMetadata:
    return BookMetadata(book_id=book_id, number=number, release_date=release_date)


@dataclass
class SeriesTestData:
    series: Series
    series_metadata: SeriesMetadata
    book: Book
    book_metadata: BookMetadata


@dataclass
class TestCase:
    id: str
    data: SeriesTestData | None = None
    expected: str | None = None
    user_input: str | None = None
    log: str | None = None
    path: str | None = None
    share_files: dict[str, str] | None = None
    library_files: dict[str, str] | None = None
    dry_run: bool = False


# ---- get_release_year ----
GET_RELEASE_YEAR_SUCCESS: Final[list[TestCase]] = [
    TestCase(
        id="get_release_year: success",
        data=SeriesTestData(
            create_test_series(),
            create_test_series_metadata(),
            create_test_book(),
            create_test_book_metadata(),
        ),
        expected=tc.TEST_YEAR,
        log="",
    ),
]
GET_RELEASE_YEAR_ERROR: Final[list[TestCase]] = [
    TestCase(
        id="get_release_year: no first issue no year",
        data=SeriesTestData(
            create_test_series(name=tc.ERROR_SERIES_NAME),
            create_test_series_metadata(),
            create_test_book(),
            create_test_book_metadata(number="100"),
        ),
        log=f"No first issue, or year, found in {tc.ERROR_SERIES_NAME}",
    ),
    TestCase(
        id="get_release_year: empty release date",
        data=SeriesTestData(
            create_test_series(),
            create_test_series_metadata(),
            create_test_book(),
            create_test_book_metadata(release_date="    "),
        ),
        log=f"Invalid release date for {tc.TEST_SERIES_NAME}:     ",
    ),
]
GET_RELEASE_YEAR_INPUT: Final[list[TestCase]] = [
    TestCase(
        id="get_release_year: no first issue",
        data=SeriesTestData(
            create_test_series(),
            create_test_series_metadata(),
            create_test_book(),
            create_test_book_metadata(number="100"),
        ),
        expected="1999",
    ),
]

# ---- make_korrection ----
MAKE_KORRECTION_SUCCESS: Final[list[TestCase]] = [
    TestCase(
        id="make_korrection: success",
        data=SeriesTestData(
            create_test_series(),
            create_test_series_metadata(),
            create_test_book(),
            create_test_book_metadata(),
        ),
        expected=tc.GOOD_TITLE,
        log=f"({tc.BAD_TITLE}) -> ({tc.GOOD_TITLE})",
    ),
    TestCase(
        id="make_korrection: success with single quote",
        data=SeriesTestData(
            create_test_series(name="Test's Series v1 (1999)"),
            create_test_series_metadata(title="Test's Series"),
            create_test_book(),
            create_test_book_metadata(),
        ),
        expected="Test's Series (1999)",
        log="(Test's Series) -> (Test's Series (1999))",
    ),
]
MAKE_KORRECTION_ERROR: Final[list[TestCase]] = [
    TestCase(
        id="make_korrection: already correct",
        data=SeriesTestData(
            create_test_series(),
            create_test_series_metadata(title=tc.GOOD_TITLE),
            create_test_book(),
            create_test_book_metadata(),
        ),
        log=f"{tc.TEST_SERIES_NAME} is already correct [{tc.GOOD_TITLE}]",
    ),
    TestCase(
        id="make_korrection: manual lock",
        data=SeriesTestData(
            create_test_series(),
            create_test_series_metadata(title_lock=True),
            create_test_book(),
            create_test_book_metadata(),
        ),
        log=f"{tc.TEST_SERIES_NAME} is manually locked by user.",
    ),
]

# ---- korrect_comic_info ----
KORRECT_COMIC_INFO_SUCCESS: Final[list[TestCase]] = [
    TestCase(
        id="korrect_comic_info: normal comic info",
        path=tc.TEST_CBZ_PATH,
        expected=tc.GOOD_COMIC_INFO,
    ),
]
KORRECT_COMIC_INFO_ERROR: Final[list[TestCase]] = [
    TestCase(
        id="korrect_comic_info: already correct comic info",
        path=tc.KORRECTED_COMIC_PATH,
        expected=tc.KORRECTED_COMIC_INFO_PATH,
        log="is already correct",
    ),
    TestCase(
        id="korrect_comic_info: no cbz file",
        path="tests/test_assets/does_not_exist.cbz",
        log="No cbz found for",
    ),
    TestCase(
        id="korrect_comic_info: no ComicInfo.xml",
        path=tc.NO_COMIC_INFO_PATH,
        log="No ComicInfo.xml found in",
    ),
]
