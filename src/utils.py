"""
Utility functions and constants for the NRWE scraper.

This module provides shared configuration, data structures, and helper functions
used across the scraping, downloading, and parsing modules. It defines directory
paths, HTTP headers, and utility functions for date handling and file operations.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import TypedDict

# Project root directory derived from this file's location
_PROJECT_DIR = Path(__file__).resolve().parent.parent

# Directory structure for storing scraped data
DATA_DIR = _PROJECT_DIR / "data"  # Main data directory
IDS_DIR = DATA_DIR / "ids"  # Scraped case IDs and links
DOCS_DIR = DATA_DIR / "docs"  # Downloaded HTML documents
DOCS_PARSED_PATH = DATA_DIR / "parsed_docs.jsonl"  # Parsed structured data

# WebDriver executable path - validates existence at import time
EXECUTABLE_PATH = _PROJECT_DIR / "edgedriver_win64" / "msedgedriver.exe"
if not EXECUTABLE_PATH.exists():
    raise FileNotFoundError(
        f"Executable not found at {EXECUTABLE_PATH}. "
        "Please ensure the Edge WebDriver is installed correctly."
    )

# HTTP headers to mimic a real browser and avoid blocking
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/88.0.4324.150 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;"
    "q=0.9,image/avif,image/webp,image/apng,*/*;"
    "q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",  # Do Not Track header
}


class ResultItem(TypedDict):
    """Type definition for scraped result items.

    Represents a single case result extracted from the court database,
    containing metadata about when and where it was found along with
    the case information and link.
    """

    datetime: datetime  # Timestamp when the item was scraped
    page: int  # Page number where the item was found
    text: str  # Display text of the case link
    href: str  # URL to the full case document


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects.

    Converts datetime objects to ISO format strings for JSON serialization.
    Used when writing ResultItem objects to JSON files.
    """

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def format_date(date: datetime) -> str:
    """Format datetime as YYYYMMDD string for file naming.

    Args:
        date: DateTime object to format

    Returns:
        String in YYYYMMDD format (e.g., "20231215")
    """
    return date.strftime("%Y%m%d")


def get_output_file(start_date: datetime, end_date: datetime) -> Path:
    """Generate output file path for a date range.

    Creates a standardized filename for storing scraped case IDs
    based on the date range being processed.

    Args:
        start_date: Beginning of the date range
        end_date: End of the date range

    Returns:
        Path object for the output JSONL file

    Example:
        get_output_file(datetime(2023,12,1), datetime(2023,12,31))
        -> Path("data/ids/ids_from_20231201_to_20231231.jsonl")
    """
    return (
        IDS_DIR / f"ids_from_{format_date(start_date)}_to_{format_date(end_date)}.jsonl"
    )


def get_end_of_month(date: datetime) -> datetime:
    """Calculate the last day of the month for a given date.

    Args:
        date: Input datetime to find the month end for

    Returns:
        DateTime representing the last day of the same month

    Example:
        get_end_of_month(datetime(2023, 12, 15))
        -> datetime(2023, 12, 31)
    """
    month = date.month
    year = date.year
    if month == 12:
        month = 1
        year += 1
    else:
        month += 1
    return datetime(year=year, month=month, day=1) - timedelta(days=1)
