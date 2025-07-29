from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, declarative_base


Base = declarative_base()


class Series(Base):
    __tablename__ = "series"

    id = Column(String, primary_key=True)
    name = Column(String)
    oneshot = Column(Boolean)

    books = relationship("Book", backref="series")
    series_metadata = relationship("SeriesMetadata", backref="series")


class SeriesMetadata(Base):
    __tablename__ = "series_metadata"

    series_id = Column(String, ForeignKey("series.id"), primary_key=True)
    title = Column(String)
    title_lock = Column(Boolean)


class Book(Base):
    __tablename__ = "book"

    id = Column(String, primary_key=True)
    series_id = Column(String, ForeignKey("series.id"))
    url = Column(String)

    book_metadata = relationship("BookMetadata", backref="book")


class BookMetadata(Base):
    __tablename__ = "book_metadata"

    book_id = Column(String, ForeignKey("book.id"), primary_key=True)
    number = Column(String)
    release_date = Column(String)
