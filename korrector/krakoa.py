"""Provides classes and methods to interact with the Komga REST API."""

import logging
import re
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)


@dataclass
class Link:
    """A link associated with a series in the Komga database.

    Attributes:
        label (str): The label for the link.
        url (str): The URL of the link.

    """

    label: str
    url: str


@dataclass
class Series:
    """A series in the Komga database.

    Attributes:
        id (str): The unique identifier for the series.
        name (str): The name of the series.
        release_date (str | None): The release date of the series.
        oneshot (bool): Indicates if the series is a one-shot.
        title_lock (bool): Indicates if the title can be manually adjusted.
        sort_title (str | None): The sort title for the series.
        links (list[Link]): A list of links associated with the series.

    """

    id: str
    name: str
    release_date: str | None = None
    oneshot: bool = False
    title_lock: bool = False
    sort_title: str | None = None
    links: list[Link] = None

    @classmethod
    def from_json(cls, response: dict) -> "Series":
        """Create a Series instance from a JSON response.

        Args:
            response (dict): The JSON response from the API.

        Returns:
            Series: The created Series instance.

        """
        return cls(
            id=response["id"],
            name=response["name"],
            release_date=response.get("releaseDate"),
            oneshot=response.get("oneshot", False),
            title_lock=response.get("titleLock", False),
            sort_title=response.get("sortTitle"),
            links=[
                Link(label=link["label"], url=link["url"]) for link in response.get("links", [])
            ],
        )


class Krakoa:
    """A class to interact with the Komga REST API for series management.

    Attributes:
        api_key (str): The API key for authentication.
        api_base_url (str): The base URL of the Komga API.
        headers (dict): The headers to use for API requests.

    """

    def __init__(self, api_key: str, api_base_url: str) -> None:
        """Initialize the Krakoa instance with API key and base URL.

        Args:
            api_key (str): The API key for authentication.
            api_base_url (str): The base URL of the Komga API.

        """
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
        }

    def make_request(
        self,
        method: str,
        url: str,
        headers: dict,
        data: dict | None = None,
    ) -> dict | None:
        """Make an HTTP request to the Komga API.

        Args:
            method (str): The HTTP method to use (e.g., 'GET', 'POST').
            url (str): The URL to send the request to.
            headers (dict): The headers to include in the request.
            data (dict, optional): The JSON data to send with the request.

        Returns:
            dict: The JSON response from the API, or None if the request failed.

        """
        try:
            request_funcs = {
                "GET": lambda: requests.get(url, headers=headers, timeout=10),
                "POST": lambda: requests.post(url, json=data, headers=headers, timeout=10),
            }
            if method not in request_funcs:
                msg = f"Unsupported HTTP method: {method}"
                raise ValueError(msg)
            resp = request_funcs[method]()
            resp.raise_for_status()
            return resp.json()
        except requests.Timeout:
            logger.exception("Request to %s timed out after 10 seconds [%s]", url, method)
        except requests.RequestException:
            logger.exception("HTTP error for %s [%s]: ", url, method)
        return None

    def get_release_year(
        self,
        series_id: str,
        series_name: str,
        default: bool = False,
    ) -> str | None:
        """Get the release year for a series using the Komga REST API.

        Args:
            series_id (str): The series ID to fetch books for.
            series_name (str): The name of the series (for fallback year guess).
            default (bool, optional): If True, will prompt the user to enter the year manually.

        Returns:
            str: The release year as a string, or None if no year could be determined.

        """
        url = f"{self.api_base_url}/books/filter"
        data = {
            "condition": {
                "seriesId": {
                    "operator": "is",
                    "value": series_id,
                },
            },
        }
        resp = self.make_request(url, self.headers, data)
        books = resp.json().get("content", [])

        # Try to find the first issue (number == "1")
        first = next((book for book in books if book.get("number") == "1"), None)
        if first is not None:
            release_date = first.get("releaseDate")
            pattern = re.compile(r"\d{4}-\d{2}-\d{2}")
            if not release_date or not pattern.match(release_date):
                logger.warning("Invalid release date found for series '%s'.", series_name)
                return None
            return release_date.split("-")[0]

        # Guess the year from the series name if no first issue is found
        name = series_name or ""
        match = re.search(r"\((\d{4})\)", name)
        if match is None:
            logger.warning("No first issue or year found in '%s'", name)
            return None
        year = match.group(1)

        # prompt user offering guess year as default
        if default:
            return year
        response = input(
            f"No first issue found for {name}. Enter year manually (Default: {year}): ",
        )
        return response or year

    @staticmethod
    def _generate_sort_title(title: str) -> str:
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

    def make_korrection(self, series_id: str, title: str) -> None:
        """Update the metadata of a series with a new title and sort title.

        Sends a PUT request to the API to update the series metadata, locking
        both the title and sort title fields.

        Args:
            series_id (str): The unique identifier of the series to update.
            title (str): The new title to set for the series.

        Raises:
            requests.HTTPError: If the HTTP request to update the metadata fails.

        """
        url = f"{self.api_base_url}/series/{series_id}/metadata"
        data = {
            "title": title,
            "titleLock": True,
            "sortTitle": self._generate_sort_title(title),
            "sortTitleLock": True,
        }
        self.make_request(url, self.headers, data)

    def get_all_series(self, page: int = 0, size: int = 100) -> list[Series]:
        """Fetch all series from the Komga API.

        Args:
            page (int): The page number to fetch.
            size (int): The number of series per page.

        Returns:
            list[dict]: A list of series dictionaries.

        """
        url = f"{self.api_base_url}/series?page={page}&size={size}"
        resp = self.make_request(url, self.headers)
        return [Series.from_json(s) for s in resp.json().get("content", [])]
