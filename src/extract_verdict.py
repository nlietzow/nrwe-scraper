"""
Verdict extraction module for the NRWE scraper.

This module extracts verdict information from HTML documents by parsing
specific text patterns that represent different legal document formats.
It supports two different verdict formats and returns structured data.
"""

import re
from enum import StrEnum, auto

from lxml import html


class Format(StrEnum):
    """Enumeration of supported verdict formats."""

    FORMAT_1 = auto()  # Format with "Tatbestand" and "Entscheidungsgründe"
    FORMAT_2 = auto()  # Format with "Bezugnahme" and "Begründung"
    INVALID = auto()  # Invalid or unrecognized format


# Regex pattern for Format 1: Matches "Tatbestand" and "Entscheidungsgründe" sections
# Allows for spaced characters and optional colons after section headers
pattern_1 = re.compile(
    (
        r"\s*T\s*a\s*t\s*b\s*e\s*s\s*t\s*a\s*n\s*d\s*:?"
        r"\s*\n(.*?)\n"
        r"\s*E\s*n\s*t\s*s\s*c\s*h\s*e\s*i\s*d\s*u\s*n\s*g\s*s\s*g\s*r\s*ü\s*n\s*d\s*e\s*:?"
        r"\s*\n(.*?)\Z"
    ),
    re.DOTALL | re.IGNORECASE,
)

# Regex pattern for Format 2: Matches "Gründe" with Roman numeral sections I. and II.
# Stops at section III. or end of text
pattern_2 = re.compile(
    (
        r"\s*G\s*r\s*ü\s*n\s*d\s*e\s*:?\s*\n"
        r"\s*I\s*\.\s*\n(.*?)\n"
        r"\s*II\s*\.\s*\n(.*?)"
        r"(?:\n\s*III\s*\.\s*\n|\Z)"
    ),
    re.DOTALL | re.IGNORECASE,
)


def extract_verdict(div: html.HtmlElement):
    """Extract verdict information from HTML element.

    Parses HTML content by extracting text from paragraph elements with class
    "absatzLinks" and matches it against predefined patterns to identify the
    verdict format and extract structured data.

    Args:
        div (html.HtmlElement): The HTML element containing the verdict text.

    Returns:
        dict: Dictionary containing extracted information with format type and
              relevant fields, or format=INVALID if no pattern matches.

              For FORMAT_1: {"format": Format.FORMAT_1, "tatbestand": str, "entscheidungsgründe": str}
              For FORMAT_2: {"format": Format.FORMAT_2, "bezugnahme": str, "begruendung": str}
              For INVALID: {"format": Format.INVALID}
    """
    # Extract and clean text from specific HTML elements
    text = "\n\n".join(
        " ".join(p.text_content().split())
        for p in div.xpath('//p[@class="absatzLinks"]')
        if p.text_content().strip()
    )
    return _match_pattern(text)


def _match_pattern(text: str):
    """Match text against predefined patterns to identify format and extract data.

    Attempts to match the input text against two different legal document formats:
    - Format 1: Documents with "Tatbestand" and "Entscheidungsgründe" sections
    - Format 2: Documents with "Gründe" and Roman numeral sections (I., II.)

    Args:
        text (str): The cleaned text content to be matched against patterns.

    Returns:
        dict: Dictionary with extracted information:
              - If Format 1 matches: format, tatbestand, entscheidungsgründe
              - If Format 2 matches: format, bezugnahme, begruendung
              - If no match: format=INVALID
    """
    # Check for Format 1
    match = pattern_1.match(text)
    if match:
        return {
            "format": Format.FORMAT_1,
            "tatbestand": match.group(1),
            "entscheidungsgründe": match.group(2),
        }

    # Check for Format 2
    match = pattern_2.match(text)
    if match:
        return {
            "format": Format.FORMAT_2,
            "bezugnahme": match.group(1),
            "begruendung": match.group(2),
        }

    # Return invalid format if no patterns match
    return {"format": Format.INVALID}
