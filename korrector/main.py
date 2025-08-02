"""Provides functionality to correct comic book series titles."""

import logging
import re

from korrector.krakoa import Krakoa

from .orm import Series

# TODO @pickled-dev: figure out how to configure api stuff
# https://github.com/pickled-dev/korrector/issues/4
api_key = "18908d8a6f874536bcc6f916faed0437"
api_base_url = "http://192.168.1.93:25600/api/v1"

logger = logging.getLogger(__name__)


def generate_sort_title(title: str) -> str:
    """Generate a sort title by removing leading articles (e.g., 'The', 'A', 'An').

    Args:
        title (str): The original title.

    Returns:
        str: The sort title with leading articles removed and whitespace stripped.

    """
    articles = ("the ", "a ", "an ")
    title_lower = title.lower().lstrip()
    for article in articles:
        if title_lower.startswith(article):
            return title[len(article) :].lstrip()
    return title.lstrip()


def korrect_series(series: Series, k: Krakoa, dry_run: bool = False) -> None:
    """Correct the title of a series by appending its release year if not already present.

    This function checks if the series title is locked, already contains a year, or lacks a release
    date. If none of these conditions are met, it constructs a new title by appending the release
    year to the series name, generates a new sort title, and applies the correction using the
    provided Krakoa instance.

    Args:
        series (Series): The series object to correct.
        k (Krakoa): Instance of Krakoa used to apply the correction.
        dry_run (bool, optional): If True, performs a dry run without making changes.

    Returns:
        None

    """
    if series.title_lock:
        logger.debug("Skipping series %s as title_lock is set.", series.name)
        return
    if "(" in series.title and ")" in series.title:
        logger.debug("Series %s already has a year in the title. (%s)", series.name, series.title)
        return
    if not series.release_date:
        logger.warning("No release date for series %s, skipping.", series.name)
        return
    clean_title = re.sub(r"\s*(?:#\d+\s*)?\(\d{4}\)$", "", series.name)
    new_title = f"{clean_title} ({series.release_date.split('-')[0]})"
    new_sort = generate_sort_title(new_title)
    logger.info("[%s -> %s]", series.title, new_title)
    if not dry_run:
        k.make_korrection(series.id, new_title, new_sort)


def korrect_database(dry_run: bool = False) -> None:
    """Corrects all series in the database using the Krakoa API.

    Args:
        dry_run (bool, optional): If True, performs a dry run without making changes.

    Returns:
        None

    """
    k = Krakoa(api_key=api_key, api_base_url=api_base_url)
    series = k.get_all_series()
    for s in series:
        korrect_series(s, k, dry_run)
