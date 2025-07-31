import logging
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote

import pytest
import sqlalchemy.orm as alch
from lxml import etree
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import tests.test_data as td
from korrector import main
from korrector.orm import Base, Book, BookMetadata, Series, SeriesMetadata


@pytest.fixture
def db() -> alch.Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def add_test_series(
    series: Series,
    series_metadata: SeriesMetadata,
    test_session: alch.Session,
) -> None:
    test_session.add(series)
    test_session.add(series_metadata)


def add_test_book(
    book: Book,
    book_metadata: BookMetadata,
    test_session: alch.Session,
) -> None:
    test_session.add(book)
    test_session.add(book_metadata)


@pytest.fixture(name="case")
def setup_test_data(request: pytest.FixtureRequest, db: alch.Session) -> dict:
    case = request.param
    add_test_series(case["series"], case["series_metadata"], db)
    add_test_book(case["book"], case["book_metadata"], db)
    db.commit()
    return case


# get_release_year
@pytest.mark.parametrize(
    ("case", "expected", "log"),
    [
        (
            td.VALID_SERIES["case"],
            td.VALID_SERIES["expected"],
            td.VALID_SERIES["log"],
        ),
    ],
    indirect=["case"],
    ids=["valid_series"],
)
def test_get_release_year(
    case: dict,
    expected: str,
    log: str,
    db: alch.Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    result = main.get_release_year(case.series)
    assert result == expected
    assert log in caplog.text


@pytest.mark.parametrize(
    ("case", "log"),
    [
        (
            td.NO_FIRST_ISSUE_NO_YEAR["case"],
            td.NO_FIRST_ISSUE_NO_YEAR["log"],
        ),
        (
            td.EMPTY_RELEASE_DATE["case"],
            td.EMPTY_RELEASE_DATE["log"],
        ),
    ],
    indirect=["case"],
    ids=["no_first_issue_no_year", "empty_release_date"],
)
def test_get_release_year_error(
    case: dict,
    log: str,
    db: alch.Session,
) -> None:
    with pytest.raises(ValueError, match=re.escape(log)):
        main.get_release_year(case.series)


@pytest.mark.parametrize(
    ("case", "user_input", "expected"),
    [
        (
            td.NO_FIRST_ISSUE["case"],
            td.NO_FIRST_ISSUE["user_input"],
            td.NO_FIRST_ISSUE["expected"],
        ),
    ],
    indirect=["case"],
    ids=["no_first_issue"],
)
def test_get_release_year_input(
    case: dict,
    user_input: str,
    expected: str,
    db: alch.Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_input(prompt: str) -> str:
        return user_input

    monkeypatch.setattr("builtins.input", mock_input)
    result = main.get_release_year(case.series)
    assert result == expected


# make_korrection
@pytest.mark.parametrize(
    ("case", "expected", "log"),
    [
        (
            td.STANDARD_KORRECTION["case"],
            td.STANDARD_KORRECTION["expected"],
            td.STANDARD_KORRECTION["log"],
        ),
    ],
    indirect=["case"],
    ids=["standard_korrection"],
)
def test_make_korrection(
    case: dict,
    expected: str,
    log: str,
    db: alch.Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    main.make_korrection(case.series)
    result = db.query(SeriesMetadata).filter_by(series_id=case.series.id).first().title
    assert result == expected
    assert log in caplog.text


@pytest.mark.parametrize(
    ("case", "log"),
    [
        (
            td.ALREADY_CORRECT["case"],
            td.ALREADY_CORRECT["log"],
        ),
        (
            td.MANUAL_LOCK["case"],
            td.MANUAL_LOCK["log"],
        ),
    ],
    indirect=["case"],
    ids=["already_correct", "manual_lock"],
)
def test_make_korrection_error(
    case: dict,
    log: str,
    db: alch.Session,
) -> None:
    with pytest.raises(ValueError, match=re.escape(log)):
        main.make_korrection(case.series)


# korrect comic info
@pytest.mark.parametrize(
    ("case", "expected"),
    [
        (
            td.NORMAL_COMIC_INFO["case"],
            td.NORMAL_COMIC_INFO["expected"],
        ),
    ],
    indirect=["case"],
    ids=["normal_comic_info"],
)
def test_korrect_comic_info(
    case: dict,
    expected: str,
    db: alch.Session,
) -> None:
    # Arrange
    path = unquote(case["book"].url)
    original = Path(re.sub(r"file://?", "", path))
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)
        copied = shutil.copy(original, tmpdir)
        case["book"].url = f"file://{copied}"
        db.add(case["book"])
        db.commit()

        # Act
        main.korrect_comic_info(case.series, db, False)
        with zipfile.ZipFile(copied, "r") as cbz:
            cbz.extract("ComicInfo.xml", tmpdir)
        tree_result = etree.parse(f"{tmpdir}/ComicInfo.xml")
        tree_expected = etree.parse(expected)

        # Assert
        assert etree.tostring(tree_result.getroot()) == etree.tostring(
            tree_expected.getroot(),
        )


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        (
            td.NO_TITLE_COMIC_INFO["case"],
            td.NO_TITLE_COMIC_INFO["expected"],
        ),
        (
            td.BAD_PATH_COMIC_INFO["case"],
            td.BAD_PATH_COMIC_INFO["expected"],
        ),
        (
            td.NO_COMIC_INFO["case"],
            td.NO_COMIC_INFO["expected"],
        ),
        (
            td.NO_DATE_COMIC_INFO["case"],
            td.NO_DATE_COMIC_INFO["expected"],
        ),
        (
            td.KORRECTED_COMIC_INFO["case"],
            td.KORRECTED_COMIC_INFO["expected"],
        ),
    ],
    indirect=["case"],
    ids=[
        "no title",
        "no cbz",
        "no ComicInfo.xml",
        "no date",
        "korrected",
    ],
)
def test_korrect_comic_info_error(
    case: dict,
    expected: str,
    db: alch.Session,
) -> None:
    original = Path(re.sub(r"file://?", "", unquote(case["book"].url)))
    # CASE: File does not exist
    if not original.exists():
        with pytest.raises(FileNotFoundError, match=re.escape(expected)):
            main.korrect_comic_info_database(case.series, db, False)
        return

    # Arrange
    # copy test data to temp dir
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)
        copied = shutil.copy(original, tmpdir)
        case["book"].url = f"file://{copied}"
        db.add(case["book"])
        db.commit()

        # Act & Assert
        try:
            main.korrect_comic_info_database(case.series, db, False)
        except (ValueError, FileNotFoundError) as e:
            assert expected in str(e)
        else:
            pytest.fail("Expected ValueError or FileNotFoundError not raised")
