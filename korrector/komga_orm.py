from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Series(Base):
    __tablename__ = 'series'

    id = Column(String, primary_key=True)
    name = Column(String)
    oneshot = Column(Integer)

    books = relationship("BookTable", backref="series")
    series_metadata = relationship("SeriesMetadataTable", backref="series")


class SeriesMetadata(Base):
    __tablename__ = 'series_metadata'
    series_id = Column(String, ForeignKey('series.id'), primary_key=True)
    title = Column(String)
    locked = Column(Boolean)


class Book(Base):
    __tablename__ = 'book'
    id = Column(Integer, primary_key=True)
    series_id = Column(String, ForeignKey('series.id'))
    url = Column(String)

    book_metadata = relationship("BookMetadataTable", backref="book")


class BookMetadata(Base):
    __tablename__ = 'book_metadata'
    book_id = Column(String, ForeignKey('book.id'), primary_key=True)
    number = Column(String)
    release_date = Column(String)
