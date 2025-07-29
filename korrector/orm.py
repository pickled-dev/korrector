"""SQLAlchemy ORM classes for the Komga database.

This module contains the ORM classes necessary to interact with a Komga database
using SQLAlchemy.
"""

from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Series(Base):
    """A series in the Komga database.

    Attributes:
        id (str): The unique identifier for the series.
        name (str): The name of the series.
        oneshot (bool): A boolean indicating whether the series is a one-shot or
            not.
        books (list[Book]): A list of books in the series.
        series_metadata (SeriesMetadata): The metadata for the series.

    """

    __tablename__ = "series"

    id = Column(String, primary_key=True)
    name = Column(String)
    oneshot = Column(Boolean)

    books = relationship("Book", backref="series")
    series_metadata = relationship("SeriesMetadata", backref="series")


class SeriesMetadata(Base):
    """Metadata for a series in the Komga database.

    The title field in this table is what Komga will look at when attempting
    to import a reading list.

    Attributes:
        series_id (str): The unique identifier linking the metadata to a series.
        title (str): The title of the series.
        title_lock (bool): A boolean indicating if the title can be manually adjusted.

    """

    __tablename__ = "series_metadata"

    series_id = Column(String, ForeignKey("series.id"), primary_key=True)
    title = Column(String)
    title_lock = Column(Boolean)


class Book(Base):
    """A book in the Komga database.

    Attributes:
        id (str): The unique identifier for the book.
        series_id (str): The unique identifier for the series that the book belongs to.
        url (str): The path to the book.
        book_metadata (BookMetadata): The metadata for the book.

    """

    __tablename__ = "book"

    id = Column(String, primary_key=True)
    series_id = Column(String, ForeignKey("series.id"))
    url = Column(String)

    book_metadata = relationship("BookMetadata", backref="book")


class BookMetadata(Base):
    """Metadata for a book in the Komga database.

    Attributes:
        book_id (str): The unique identifier linking the metadata to a book.
        number (str): The number of the book in the series.
        release_date (str): The date the book was released.

    """

    __tablename__ = "book_metadata"

    book_id = Column(String, ForeignKey("book.id"), primary_key=True)
    number = Column(String)
    release_date = Column(String)
