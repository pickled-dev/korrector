import logging
import re

import pytest
import sqlalchemy.orm as alch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from korrector import main
from korrector.orm import Base, Book, BookMetadata, Series, SeriesMetadata

from . import test_data as td


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


@pytest.fixture
def setup_test_data(request: pytest.FixtureRequest, db: alch.Session) -> dict:
    case = request.param
    add_test_series(case["series"], case["series_metadata"], db)
    add_test_book(case["book"], case["book_metadata"], db)
    db.commit()
    return case


# get_release_year
@pytest.mark.parametrize(
    ("setup_test_data", "expected", "log"),
    [
        (
            td.VALID_SERIES["case"],
            td.VALID_SERIES["expected"],
            td.VALID_SERIES["log"],
        ),
    ],
    indirect=["setup_test_data"],
)
def test_get_release_year(
    setup_test_data: dict,
    expected: str,
    log: str,
    db: alch.Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    result = main.get_release_year(setup_test_data["series"], db)
    assert result == expected
    assert log in caplog.text


@pytest.mark.parametrize(
    ("setup_test_data", "log"),
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
    indirect=["setup_test_data"],
)
def test_get_release_year_error(
    setup_test_data: dict,
    log: str,
    db: alch.Session,
) -> None:
    with pytest.raises(ValueError, match=re.escape(log)):
        main.get_release_year(setup_test_data["series"], db)


@pytest.mark.parametrize(
    ("setup_test_data", "user_input", "expected"),
    [
        (
            td.NO_FIRST_ISSUE["case"],
            td.NO_FIRST_ISSUE["user_input"],
            td.NO_FIRST_ISSUE["expected"],
        ),
    ],
    indirect=["setup_test_data"],
)
def test_get_release_year_input(
    setup_test_data: dict,
    user_input: str,
    expected: str,
    db: alch.Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_input(prompt: str) -> str:
        return user_input

    monkeypatch.setattr("builtins.input", mock_input)
    result = main.get_release_year(setup_test_data["series"], db)
    assert result == expected


# make_korrection
@pytest.mark.parametrize(
    ("setup_test_data", "expected", "log"),
    [
        (
            td.STANDARD_KORRECTION["case"],
            td.STANDARD_KORRECTION["expected"],
            td.STANDARD_KORRECTION["log"],
        ),
    ],
    indirect=["setup_test_data"],
)
def test_make_korrection(
    setup_test_data: dict,
    expected: str,
    log: str,
    db: alch.Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    main.make_korrection(setup_test_data["series"], db)
    result = (
        db.query(SeriesMetadata)
        .filter_by(series_id=setup_test_data["series"].id)
        .first()
        .title
    )
    assert result == expected
    assert log in caplog.text


@pytest.mark.parametrize(
    ("setup_test_data", "log"),
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
    indirect=["setup_test_data"],
)
def test_make_korrection_error(
    setup_test_data: dict,
    log: str,
    db: alch.Session,
) -> None:
    with pytest.raises(ValueError, match=re.escape(log)):
        main.make_korrection(setup_test_data["series"], db)
