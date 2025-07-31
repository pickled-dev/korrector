"""Test suite for the korrector module.

This file contains unit tests for the korrector package, focusing on database
operations, metadata correction, and ComicInfo.xml file handling. It uses pytest
fixtures and test data from in the form of a `TestCase` class to
simulate various scenarios and validate the functionality of the korrector module.

See tests/test_data.py for the data model of `TestCase`
"""

import logging
import re
import shutil
import tempfile
import typing
import zipfile
from pathlib import Path

import pytest
import sqlalchemy.orm as alch
from lxml import etree
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import tests.test_data as td
from korrector import main
from korrector.orm import Base, Book, BookMetadata, Series, SeriesMetadata


@pytest.fixture
def db() -> typing.Generator[alch.Session]:
    """
    Creates a SQLAlchemy in-memory SQLite database session for testing purposes.

    This generator function sets up the database schema, yields a session for use in
    tests, and ensures proper cleanup by closing the session and disposing of the
    engine after use.

    Yields:
        alch.Session: A SQLAlchemy session connected to an in-memory SQLite database.
    """
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
    add_test_series(case.data.series, case.data.series_metadata, db)
    add_test_book(case.data.book, case.data.book_metadata, db)
    db.commit()
    return case


# ---- get_release_year ----
@pytest.mark.parametrize(
    "case",
    td.GET_RELEASE_YEAR_SUCCESS,
    ids=[case.id for case in td.GET_RELEASE_YEAR_SUCCESS],
    indirect=True,
)
def test_get_release_year_success(
    case: td.TestCase,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    result = main.get_release_year(case.data.series)
    assert result == case.expected
    assert case.log in caplog.text


@pytest.mark.parametrize(
    "case",
    td.GET_RELEASE_YEAR_ERROR,
    ids=[case.id for case in td.GET_RELEASE_YEAR_ERROR],
    indirect=True,
)
def test_get_release_year_error(
    case: td.TestCase,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    with pytest.raises(ValueError, match=re.escape(case.log)):
        main.get_release_year(case.data.series)


@pytest.mark.parametrize(
    "case",
    td.GET_RELEASE_YEAR_INPUT,
    ids=[case.id for case in td.GET_RELEASE_YEAR_INPUT],
    indirect=True,
)
def test_get_release_year_input(
    case: td.TestCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_input(prompt: str) -> str:
        return case.user_input

    monkeypatch.setattr("builtins.input", mock_input)
    result = main.get_release_year(case.data.series)
    assert result == case.expected


# ---- make_korrection ----
@pytest.mark.parametrize(
    "case",
    td.MAKE_KORRECTION_SUCCESS,
    ids=[case.id for case in td.MAKE_KORRECTION_SUCCESS],
    indirect=True,
)
def test_make_korrection_success(
    case: td.TestCase,
    db: alch.Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    main.make_korrection(case.data.series)
    result = (
        db.query(SeriesMetadata).filter_by(series_id=case.data.series.id).first().title
    )
    assert result == case.expected
    assert case.log in caplog.text


@pytest.mark.parametrize(
    "case",
    td.MAKE_KORRECTION_ERROR,
    ids=[case.id for case in td.MAKE_KORRECTION_ERROR],
    indirect=True,
)
def test_make_korrection_error(case: td.TestCase) -> None:
    with pytest.raises(ValueError, match=re.escape(case.log)):
        main.make_korrection(case.data.series)


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


# ---- korrect_comic_info ----
@pytest.mark.parametrize(
    "case",
    td.KORRECT_COMIC_INFO_SUCCESS,
    ids=[case.id for case in td.KORRECT_COMIC_INFO_SUCCESS],
)
def test_korrect_comic_info_success(case: td.TestCase) -> None:
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)
        copied_path = tmpdir / Path(case.path).name
        shutil.copy(case.path, copied_path)

        # Act
        main.korrect_comic_info(copied_path, False)
        # Extract the new ComicInfo.xml to compare
        with zipfile.ZipFile(copied_path, "r") as cbz:
            cbz.extract("ComicInfo.xml", path=tmpdir)
            extracted_path = tmpdir / "ComicInfo.xml"

        # Assert
        assert xml_files_equal(extracted_path, Path(case.expected))


@pytest.mark.parametrize(
    "case",
    td.KORRECT_COMIC_INFO_ERROR,
    ids=[case.id for case in td.KORRECT_COMIC_INFO_ERROR],
)
def test_korrect_comic_info_error(case: td.TestCase) -> None:
    # must check for non-existent cbz care first
    if not Path(case.path).exists():
        with pytest.raises(FileNotFoundError, match=re.escape(case.log)):
            main.korrect_comic_info(Path(case.path), False)
        return
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)
        copied_path = tmpdir / Path(case.path).name
        shutil.copy(case.path, copied_path)

        # Act
        with pytest.raises((ValueError, FileNotFoundError), match=case.log):
            main.korrect_comic_info(copied_path, False)
        # Extract the new ComicInfo.xml to compare
        if case.expected:
            with zipfile.ZipFile(copied_path, "r") as cbz:
                cbz.extract("ComicInfo.xml", path=tmpdir)
                extracted_path = tmpdir / "ComicInfo.xml"
                assert xml_files_equal(extracted_path, Path(case.expected))
