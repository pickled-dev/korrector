import logging
import os
import re

from korrector.krakoa import Krakoa

from .orm import Series

api_key = os.environ.get("KOMGA_API_KEY")
api_base_url = os.environ.get("KOMGA_API_BASE_URL")

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
    if series.title_lock:
        logger.info("Skipping series %s as title_lock is set.", series.id)
        return
    if "(" in series.title and ")" in series.title:
        logger.info("Series %s already has a year in the title.", series.id)
        return
    if not series.release_date:
        logger.warning("No release date for series %s, skipping.", series.id)
        return
    clean_title = re.sub(r"\s*#\d+\s*\(\d{4}\)$", "", series.name)
    new_title = f"{clean_title} ({series.release_date.split('-')[0]})"
    new_sort = generate_sort_title(new_title)
    logger.info("Updating series %s with new title: %s", series.id, new_title)
    if not dry_run:
        k.make_korrection(series.id, new_title, new_sort)


def korrect_database(dry_run: bool = False) -> None:
    k = Krakoa(api_key=api_key, api_base_url=api_base_url)
    series = k.get_all_series()
    for s in series:
        korrect_series(s, k, dry_run)
