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
    title: str | None = None
    title_lock: bool = False
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
            title=response["metadata"]["title"],
            release_date=response["booksMetadata"]["releaseDate"],
            oneshot=response["oneshot"],
            title_lock=response["metadata"]["titleLock"],
            links=[],
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
