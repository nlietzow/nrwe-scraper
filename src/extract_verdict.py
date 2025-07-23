import re
from enum import auto, StrEnum

from lxml import html


class Format(StrEnum):
    FORMAT_1 = auto()
    FORMAT_2 = auto()
    INVALID = auto()


pattern_1 = re.compile(
    (
        r"\s*T\s*a\s*t\s*b\s*e\s*s\s*t\s*a\s*n\s*d\s*:?"
        r"\s*\n(.*?)\n"
        r"\s*E\s*n\s*t\s*s\s*c\s*h\s*e\s*i\s*d\s*u\s*n\s*g\s*s\s*g\s*r\s*ü\s*n\s*d\s*e\s*:?"
        r"\s*\n(.*?)\Z"
    ),
    re.DOTALL | re.IGNORECASE
)

pattern_2 = re.compile(
    (
        r"\s*G\s*r\s*ü\s*n\s*d\s*e\s*:?\s*\n"
        r"\s*I\s*\.\s*\n(.*?)\n"
        r"\s*II\s*\.\s*\n(.*?)"
        r"(?:\n\s*III\s*\.\s*\n|\Z)"
    ),
    re.DOTALL | re.IGNORECASE
)


def extract_verdict(div: html.HtmlElement):
    """
    Parses HTML content, extracts text, and matches it against predefined patterns.

    Args:
        div (html.HtmlElement): The HTML element containing the verdict text.

    Returns:
        dict: Extracted information or invalid format marker.
    """
    # Extract and clean text from specific HTML elements
    text = "\n\n".join(
        " ".join(p.text_content().split())
        for p in div.xpath('//p[@class="absatzLinks"]')
        if p.text_content().strip()
    )
    return _match_pattern(text)


def _match_pattern(text: str):
    """
    Matches the given text against predefined patterns to identify its format and extract data.

    Args:
        text (str): The text to be matched.

    Returns:
        dict: Extracted information or invalid format marker.
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
