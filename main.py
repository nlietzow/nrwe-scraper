from datetime import datetime

from download_docs import download_docs
from parse_docs import parse_docs
from src.run_scraping import run_scraping

START_DATE = datetime(year=1970, month=1, day=1)
END_DATE = datetime(year=2024, month=12, day=31)


async def main():
    run_scraping(START_DATE, END_DATE)
    await download_docs()
    parse_docs()


if __name__ == "__main__":
    from asyncio import run

    run(main())
