"""
Document parsing module for the NRWE scraper.

This module processes HTML documents from legal case files, extracting structured
data from different sections (meta, leitsätze, tenor, verdict) and writing the
results to a JSON Lines file for further processing.
"""

import json
import logging
from pathlib import Path
from typing import TypedDict

from lxml import html
from tqdm.auto import tqdm

from extract_verdict import extract_verdict
from utils import DOCS_DIR, DOCS_PARSED_PATH


class MainDivs(TypedDict):
    """Type definition for the main divisions found in HTML documents."""

    fp: str  # File path of the source document
    meta: dict[str, str]  # Metadata fields (date, court, case number, etc.)
    leitsaetze: dict[str, str]  # Key principles and legal categories
    tenor: dict[str, str]  # Court decision summary
    verdict: dict[str, str]  # Full verdict text with reasoning
    verdict_html: str  # Raw HTML of the verdict section


def parse_docs():
    """Parse all HTML documents and write extracted data to JSON Lines file.

    Processes HTML files in the DOCS_DIR/nrwe/olgs directory recursively,
    extracting structured data from each document and appending it as a
    JSON object to the output file. Creates or clears the output file first.

    The function shows progress with a progress bar and processes files
    one by one to avoid memory issues with large datasets.
    """
    # Clear or create the output file
    with open(DOCS_PARSED_PATH, "w", encoding="utf-8"):
        pass

    # Process each HTML file in the directory
    with tqdm(desc="Parsing documents") as pbar:
        for fp in (DOCS_DIR / "nrwe" / "olgs").glob("**/*.html"):
            pbar.set_postfix(file=fp.name)
            record = _parse(fp)
            with open(DOCS_PARSED_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
            pbar.update(1)


def _parse(file: Path):
    """Parse a single HTML document to extract structured legal case data.

    Processes an HTML file by identifying different document sections (meta,
    leitsätze, tenor, verdict) and extracting relevant fields from each.
    Ensures only one section of each type exists per document.

    Args:
        file (Path): Path to the HTML file to process.

    Returns:
        dict: Merged dictionary containing all extracted fields from the document,
              including file path, metadata, legal principles, decision summary,
              and verdict information.

    Raises:
        ValueError: If multiple sections of the same type are found or if
                   duplicate keys exist between sections.
    """
    # Parse the HTML file
    tree = html.parse(file)

    # Initialize the structure to hold extracted data
    main_divs = MainDivs(
        fp=str(file.resolve().absolute()).split("data\\docs\\", 1)[1],
        meta={},
        leitsaetze={},
        tenor={},
        verdict={},
        verdict_html="",
    )

    # Process each "maindiv" element in the HTML
    for div in tree.xpath('//div[@class="maindiv"]'):
        if not div.text_content().strip():
            continue

        # Check the type of the division
        is_meta, is_leitsaetze, is_tenor, is_verdict = (
            _is_meta(div),
            _is_leitsaetze(div),
            _is_tenor(div),
            _is_verdict(div),
        )

        if sum((is_meta, is_leitsaetze, is_tenor, is_verdict)) > 1:
            logging.error(f"Multiple div types identified in {file}.")
            continue

        # Extract fields based on the type
        if is_meta:
            if main_divs["meta"]:
                raise ValueError(f"Multiple meta divisions found in {file}.")
            main_divs["meta"] = _extract_fields(div)
        elif is_leitsaetze:
            if main_divs["leitsaetze"]:
                raise ValueError(f"Multiple leitsätze divisions found in {file}.")
            main_divs["leitsaetze"] = _extract_fields(div)
        elif is_tenor:
            if main_divs["tenor"]:
                raise ValueError(f"Multiple tenor divisions found in {file}.")
            main_divs["tenor"] = _extract_fields(div)
        elif is_verdict:
            if main_divs["verdict"]:
                raise ValueError(f"Multiple urteil divisions found in {file}.")
            main_divs["verdict"] = extract_verdict(div)
            main_divs["verdict_html"] = html.tostring(div, pretty_print=True).decode(
                "utf-8"
            )
        else:
            logging.error(f"Unknown division found in {file}.")

    # Merge the extracted fields into a single dictionary
    output = main_divs["meta"]

    if set(output.keys()).intersection(main_divs["leitsaetze"].keys()):
        raise ValueError(f"Duplicate keys found between meta and leitsätze in {file}.")
    output.update(main_divs["leitsaetze"])

    if set(output.keys()).intersection(main_divs["tenor"].keys()):
        raise ValueError(f"Duplicate keys found between meta and tenor in {file}.")
    output.update(main_divs["tenor"])

    if set(output.keys()).intersection(main_divs["verdict"].keys()):
        raise ValueError(f"Duplicate keys found between meta and urteil in {file}.")
    output.update(main_divs["verdict"])

    output["verdict_html"] = main_divs["verdict_html"]

    return output


def _is_meta(div: html.HtmlElement) -> bool:
    """Check if HTML div contains metadata fields.

    Args:
        div: HTML element to check

    Returns:
        True if div contains any metadata field labels
    """
    return any(
        sub_div.text_content().strip().rstrip(":")
        in (
            "Datum",
            "Gericht",
            "Spruchkörper",
            "Entscheidungsart",
            "Aktenzeichen",
            "ECLI",
        )
        for sub_div in div.xpath('div[@class="feldbezeichnung"]')
    )


def _is_leitsaetze(div: html.HtmlElement) -> bool:
    """Check if HTML div contains legal principles (leitsätze) fields.

    Args:
        div: HTML element to check

    Returns:
        True if div contains any leitsätze field labels
    """
    return any(
        sub_div.text_content().strip().rstrip(":")
        in (
            "Vorinstanz",
            "Nachinstanz",
            "Schlagworte",
            "Normen",
            "Leitsätze",
            "Rechtskraft",
            "Sachgebiet",
        )
        for sub_div in div.xpath('div[@class="feldbezeichnung"]')
    )


def _is_tenor(div: html.HtmlElement) -> bool:
    """Check if HTML div contains tenor (decision summary) fields.

    Args:
        div: HTML element to check

    Returns:
        True if div contains tenor content or Tenor field label
    """
    if div.xpath('div[@class="feldinhalt tenor"]'):
        return True
    return any(
        sub_div.text_content().strip().rstrip(":") == "Tenor"
        for sub_div in div.xpath('div[@class="feldbezeichnung"]')
    )


def _is_verdict(div: html.HtmlElement) -> bool:
    """Check if HTML div contains verdict text content.

    Args:
        div: HTML element to check

    Returns:
        True if div contains paragraph or table elements with absatzLinks class
    """
    return bool(
        div.xpath('.//p[@class="absatzLinks"] | .//table[@class="absatzLinks"]')
    )


def _extract_fields(div: html.HtmlElement) -> dict[str, str]:
    """Extract key-value pairs from field designation and content elements.

    Args:
        div: HTML element containing feldbezeichnung and feldinhalt elements

    Returns:
        Dictionary mapping normalized field names (lowercase, no colons) to
        their corresponding text content values
    """
    return {
        " ".join(key.text_content().split())
        .lower()
        .rstrip(":"): " ".join(val.text_content().split())
        for key, val in zip(
            div.xpath('div[@class="feldbezeichnung"]'),
            div.xpath(
                'div[@class="feldinhalt"] '
                '| div[@class="feldinhalt tenor"] '
                '| div[@class="feldinhalt leitsaetze"]'
            ),
            strict=True,
        )
    }


if __name__ == "__main__":
    parse_docs()
