import json
import logging
from pathlib import Path
from typing import TypedDict

from lxml import html
from tqdm.auto import tqdm

from extract_verdict import extract_verdict
from utils import DOCS_DIR, DOCS_PARSED_PATH


class MainDivs(TypedDict):
    fp: str
    meta: dict[str, str]
    leitsaetze: dict[str, str]
    tenor: dict[str, str]
    verdict: dict[str, str]
    verdict_html: str


def parse_docs():
    """
    Parses all HTML documents in the specified directory and writes the parsed data to a JSON file.
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
    """
    Parses an individual HTML document to extract relevant fields.

    Args:
        file (Path): Path to the HTML file.

    Returns:
        dict: Extracted data from the document.
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
            main_divs["verdict_html"] = html.tostring(div, pretty_print=True).decode("utf-8")
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
    if div.xpath('div[@class="feldinhalt tenor"]'):
        return True
    return any(
        sub_div.text_content().strip().rstrip(":") == "Tenor"
        for sub_div in div.xpath('div[@class="feldbezeichnung"]')
    )


def _is_verdict(div: html.HtmlElement) -> bool:
    return bool(
        div.xpath('.//p[@class="absatzLinks"] | .//table[@class="absatzLinks"]')
    )


def _extract_fields(div: html.HtmlElement) -> dict[str, str]:
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


if __name__ == '__main__':
    parse_docs()
