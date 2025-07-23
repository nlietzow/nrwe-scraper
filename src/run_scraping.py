import json
import logging
import time
from datetime import datetime, timedelta, timezone

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm.auto import tqdm

from src.utils import (
    DateTimeEncoder,
    EXECUTABLE_PATH,
    format_date,
    get_end_of_month,
    get_output_file,
    ResultItem,
)

BASE_URL = "https://www.justiz.nrw/BS/nrwe2/index.php"
WEBDRIVER_WAIT_TIMEOUT = 60
SLEEP_TIME_PAGINATION = 1


def run_scraping(start_date: datetime, end_date: datetime):
    """
    Run the main scraping process for the given date range from start_date to end_date.
    The scraper iterates month by month, retrieving data from the specified court website.
    """
    scrape_from = start_date
    with tqdm(desc="Scraping", unit="month") as pbar:
        while True:
            if scrape_from > end_date:
                break

            scrape_to = get_end_of_month(scrape_from)
            output_file = get_output_file(scrape_from, scrape_to)
            if not output_file.exists():
                pbar.set_postfix(
                    start=format_date(scrape_from), end=format_date(scrape_to)
                )
                try:
                    results = _scrape_range(scrape_from, scrape_to)
                    output_file.write_text(
                        "\n".join(json.dumps(x, cls=DateTimeEncoder) for x in results)
                        + "\n",
                        encoding="utf-8",
                    )
                except Exception as e:
                    logging.error(
                        f"Failed to scrape range from {format_date(scrape_from)} to {format_date(scrape_to)}. "
                        f"Error: {e}"
                    )

            # Move on to the next date range
            scrape_from = scrape_to + timedelta(days=1)
            pbar.update(1)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=60), reraise=True)
def _scrape_range(start_date: datetime, end_date: datetime) -> list[ResultItem]:
    """
    Scrape all results for the specified date range from the target website.
    Uses a Selenium WebDriver to interact with the page and retrieve link results.
    """
    driver = _init_driver()
    wait = WebDriverWait(driver, WEBDRIVER_WAIT_TIMEOUT)

    try:
        # Open the target website
        driver.get(BASE_URL)

        # Wait for and submit the "otherForm2" form to proceed to search page
        other_form = wait.until(EC.presence_of_element_located((By.ID, "otherForm2")))
        driver.execute_script("arguments[0].submit();", other_form)

        # Set the dropdown fields: Gerichtstyp, Gerichtsbarkeit, Entscheidungsart
        dropdown_fields = [
            ("gerichtstyp", "Oberlandesgericht"),
            ("gerichtsbarkeit", "Ordentliche Gerichtsbarkeit"),
            ("entscheidungsart", "Urteil"),
        ]

        for field_id, field_value in dropdown_fields:
            dropdown = wait.until(EC.presence_of_element_located((By.ID, field_id)))
            select = Select(dropdown)
            select.select_by_visible_text(field_value)

        # Set the date range fields
        date_fields = [
            ("von", start_date.strftime("%d.%m.%Y")),
            ("bis", end_date.strftime("%d.%m.%Y")),
        ]

        for date_id, date_value in date_fields:
            date_field = wait.until(EC.presence_of_element_located((By.ID, date_id)))
            date_field.clear()
            date_field.send_keys(date_value)

        # Click the "Suchen" button to start the search
        absenden_button = wait.until(
            EC.presence_of_element_located((By.ID, "absenden"))
        )
        driver.execute_script("arguments[0].click();", absenden_button)

        # Iterate through all result pages to collect links
        results = []
        page = 1

        while True:
            # Wait for the results container
            results_div = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "alleErgebnisse"))
            )

            # Extract all links from the result page
            for link in results_div.find_elements(By.TAG_NAME, "a"):
                href = link.get_attribute("href")
                if href is None:
                    raise ValueError(f"Link element has no href attribute: {link}")
                results.append(
                    ResultItem(
                        datetime=datetime.now(timezone.utc),
                        page=page,
                        text=link.text,
                        href=href,
                    )
                )

            # Attempt to go to the next page; if it doesn't exist, break the loop
            try:
                next_page_button = driver.find_element(By.NAME, f"page{page + 1}")
            except NoSuchElementException:
                # No more pages
                break

            # Wait briefly before going to the next page
            time.sleep(SLEEP_TIME_PAGINATION)
            driver.execute_script("arguments[0].click();", next_page_button)
            page += 1

        return results

    finally:
        # Ensure the driver is always closed to free resources
        driver.quit()


def _init_driver(headless=True):
    """
    Initialize and return a Selenium WebDriver for Edge using the specified executable path.

    Args:
        headless (bool): If True, starts the browser in headless mode. Defaults to False.

    Returns:
        WebDriver: Configured Edge WebDriver instance.
    """
    options = Options()  # Use Options() for Edge options
    if headless:
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument(
            "--no-sandbox"
        )  # Optional: helpful in certain environments
        options.add_argument(
            "--disable-dev-shm-usage"
        )  # Optional: helpful in certain environments

    # Initialize and return the Edge WebDriver
    return webdriver.Edge(
        service=Service(executable_path=str(EXECUTABLE_PATH)), options=options
    )
