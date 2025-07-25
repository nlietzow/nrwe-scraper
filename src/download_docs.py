"""
Document download module for the NRWE scraper.

This module provides functionality to download HTML documents concurrently
from URLs extracted from JSON files. It includes URL validation, retry logic,
and progress tracking.
"""

import json
import logging
from asyncio import Semaphore, gather, timeout

from httpx import URL, AsyncClient, InvalidURL, Response
from tenacity import retry, stop_after_attempt, wait_random_exponential
from tqdm.auto import tqdm

from utils import DOCS_DIR, HEADERS, IDS_DIR

# Maximum number of concurrent downloads
CONCURRENCY = 4
# Timeout for individual HTTP requests in seconds
TIMEOUT = 60


async def download_docs(concurrency=CONCURRENCY):
    """Download documents concurrently from provided IDs.

    Reads JSON lines from files in IDS_DIR, extracts the 'href' field to form a URL,
    and downloads the HTML documents using an async HTTP client.

    Args:
        concurrency: Maximum number of concurrent downloads (default: CONCURRENCY)

    The function processes all JSONL files matching the pattern '*ids_from_*_to_*.jsonl'
    in the IDS_DIR directory. Each line should contain a JSON object with an 'href' field.
    """
    with tqdm(desc="Downloading documents") as pbar:
        async with AsyncClient(headers=HEADERS) as client:
            sem = Semaphore(concurrency)
            for file in IDS_DIR.glob("*ids_from_*_to_*.jsonl"):
                pbar.set_postfix(file=file.name)
                links = [
                    _parse_url(json.loads(line).get("href", ""))
                    for line in file.read_text("utf-8").strip().splitlines()
                ]
                try:
                    await gather(
                        *(
                            _download(url, client, sem)
                            for url in links
                            if url is not None
                        )
                    )
                except Exception as e:
                    logging.error(f"Failed to download documents: {e}")

                pbar.update(1)


def _parse_url(href: str) -> URL | None:
    """Parse and validate a URL extracted from the href field.

    Args:
        href: URL string to parse and validate

    Returns:
        URL object if valid, None otherwise

    A valid URL must meet the following criteria:
      - Must be absolute
      - Must use HTTP or HTTPS
      - Must end with .html
      - Must not contain query parameters or fragments
    """
    if not href:
        return None
    try:
        url = URL(href)
    except InvalidURL as e:
        logging.error(f"Failed to parse URL: {href}, {e}")
        return None

    # Check if URL is absolute
    if not url.is_absolute_url:
        logging.error(f"URL is not absolute: {url}")
        return None

    # Check if scheme is HTTP or HTTPS
    if url.scheme not in {"http", "https"}:
        logging.error(f"Invalid scheme: {url}")
        return None

    # Check if the path ends with .html
    if not url.path.endswith(".html"):
        logging.error(f"URL is not a HTML document: {url}")
        return None

    # Check if URL has no query or fragment
    if url.query or url.fragment:
        logging.error(f"URL contains query parameters or fragments: {url}")
        return None

    return url


@retry(
    stop=stop_after_attempt(5),
    wait=wait_random_exponential(multiplier=60),
    reraise=True,
)
async def _download(url: URL, client: AsyncClient, sem: Semaphore):
    """Download a single HTML document from the given URL.

    Uses a semaphore to limit concurrency and retries on failure
    with exponential backoff. If already downloaded, skip.

    Args:
        url: The URL to download from
        client: HTTP client for making requests
        sem: Semaphore to limit concurrent downloads

    The function creates the necessary directory structure and saves
    the HTML content to a file based on the URL path.
    """
    output_file = DOCS_DIR / url.path.lstrip("/")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # If file already exists, do not re-download
    if output_file.exists():
        return

    # Acquire semaphore to limit concurrent downloads
    async with sem:
        # Enforce timeout to avoid hanging on slow responses
        async with timeout(TIMEOUT):
            response = await client.get(url, follow_redirects=False)

    # Raise HTTPError if response is not 2xx
    response.raise_for_status()

    # Check if the response is HTML
    if not _is_html(response):
        logging.error(f"URL is not a html doc: {url}")
        return

    # Write content to disk
    with output_file.open("wb") as f:
        f.write(response.content)


def _is_html(response: Response) -> bool:
    """Check if the response content-type indicates HTML.

    Args:
        response: HTTP response object to check

    Returns:
        True if content-type starts with 'text/html', False otherwise
    """
    return (
        response.headers.get("content-type", "").lower().strip().startswith("text/html")
    )
