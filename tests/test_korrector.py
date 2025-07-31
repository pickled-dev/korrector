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
    add_test_series(case.series, case.series_metadata, db)
    add_test_book(case.book, case.book_metadata, db)
    db.commit()
    return case


# get_release_year
@pytest.mark.parametrize(
    ("case", "expected", "log"),
    [
        (
            td.GET_RELEASE_YEAR_SUCCESS["case"],
            td.GET_RELEASE_YEAR_SUCCESS["expected"],
            td.GET_RELEASE_YEAR_SUCCESS["log"],
        ),
    ],
    indirect=["case"],
    ids=["Test Get Release Year Success"],
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
    ids=["No First Issue No Year", "Empty Release Date"],
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
    ids=["No First Issue (Input)"],
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
            td.MAKE_KORRECTION_SUCCESS["case"],
            td.MAKE_KORRECTION_SUCCESS["expected"],
            td.MAKE_KORRECTION_SUCCESS["log"],
        ),
    ],
    indirect=["case"],
    ids=["Make Korrection Success"],
)
def test_make_korrection_success(
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
    ids=["Already Correct", "Manual Lock"],
)
def test_make_korrection_error(
    case: dict,
    log: str,
    db: alch.Session,
) -> None:
    with pytest.raises(ValueError, match=re.escape(log)):
        main.make_korrection(case.series)


def xml_files_equal(path1: Path, path2: Path) -> bool:
    """Logically compare two xml files.

    c14n applies canonical XML formatting normalizing attribute ordering, newlines, etc.

    Args:
        path1 (Path): The path to the first xml file.
        path2 (Path): The path to the second xml file.

    Returns:
        bool: True if the two xml files are equal, False otherwise.

    """
    tree1 = etree.parse(path1)
    tree2 = etree.parse(path2)
    return etree.tostring(tree1, method="c14n") == etree.tostring(tree2, method="c14n")


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (
            td.NORMAL_COMIC_INFO["path"],
            td.NORMAL_COMIC_INFO["expected"],
        ),
    ],
    ids=["Normal Comic Info"],
)
def test_korrect_comic_info_success(path: str, expected: str) -> None:
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)
        copied_path = tmpdir / Path(path).name
        shutil.copy(path, copied_path)

        # Act
        main.korrect_comic_info(copied_path, False)
        # Extract the new ComicInfo.xml to compare
        with zipfile.ZipFile(copied_path, "r") as cbz:
            cbz.extract("ComicInfo.xml", path=tmpdir)
            extracted_path = tmpdir / "ComicInfo.xml"

        # Assert
        assert xml_files_equal(extracted_path, Path(expected))
