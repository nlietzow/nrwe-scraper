import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import TypedDict

_PROJECT_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = _PROJECT_DIR / "data"
IDS_DIR = DATA_DIR / "ids"
DOCS_DIR = DATA_DIR / "docs"

EXECUTABLE_PATH = _PROJECT_DIR / "edgedriver_win64" / "msedgedriver.exe"

DOCS_PARSED_PATH = DATA_DIR / "parsed_docs.jsonl"

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
    "DNT": "1",
}


class ResultItem(TypedDict):
    datetime: datetime
    page: int
    text: str
    href: str


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def format_date(date: datetime):
    return date.strftime("%Y%m%d")


def get_output_file(start_date, end_date):
    return (
            IDS_DIR / f"ids_from_{format_date(start_date)}_to_{format_date(end_date)}.jsonl"
    )


def get_end_of_month(date):
    month = date.month
    year = date.year
    if month == 12:
        month = 1
        year += 1
    else:
        month += 1
    return datetime(year=year, month=month, day=1) - timedelta(days=1)
