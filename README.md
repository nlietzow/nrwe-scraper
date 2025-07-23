# NRWE Court Case Scraper

A comprehensive web scraping tool for extracting legal case information from the North Rhine-Westphalia (NRWE) court database. This project automates the process of searching, downloading, and parsing court decisions from the official NRWE justice portal.

## Overview

The NRWE scraper consists of a three-stage pipeline that:

1. **Scrapes case metadata** from the NRWE court database search interface
2. **Downloads full HTML documents** for each case
3. **Parses and extracts structured data** from the downloaded documents

## Features

- **Automated web scraping** using Selenium WebDriver
- **Concurrent document downloading** with retry logic
- **Intelligent HTML parsing** with support for multiple verdict formats
- **Date range processing** with month-by-month iteration
- **Progress tracking** with visual progress bars
- **Robust error handling** and logging
- **Structured data output** in JSON Lines format

## Installation

### Prerequisites

- Python 3.8 or higher
- Microsoft Edge browser
- Microsoft Edge WebDriver

### 1. Clone the Repository

```bash
git clone <repository-url>
cd nrwe-scraper
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Download and Setup Microsoft Edge WebDriver

#### Option A: Automatic Download (Recommended)

1. Visit the [Microsoft Edge WebDriver page](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/)
2. Download the version that matches your Edge browser version
3. Extract the downloaded archive
4. Create a directory structure in your project root:

```
nrwe-scraper/
├── edgedriver_win64/
│   └── msedgedriver.exe
├── src/
├── main.py
└── requirements.txt
```

#### Option B: Using WebDriver Manager (Alternative)

If you prefer automated driver management, you can modify the code to use `webdriver-manager`:

```bash
pip install webdriver-manager
```

Then update `src/utils.py` to use the WebDriverManager instead of the hardcoded path.

#### Verifying Edge Browser Version

To check your Edge browser version:
1. Open Microsoft Edge
2. Click the three dots menu (⋯) in the top right
3. Go to Help and feedback → About Microsoft Edge
4. Note the version number and download the matching WebDriver

### 4. Create Data Directories

The scraper will automatically create the required directories, but you can create them manually:

```bash
mkdir -p data/ids data/docs
```

## Usage

### Quick Start

Run the complete pipeline with default settings:

```bash
python main.py
```

This will:
1. Scrape court cases from 1970-2024
2. Download all found documents
3. Parse and extract structured data

### Pipeline Components

The scraping pipeline consists of three main stages:

#### Stage 1: Web Scraping (`run_scraping`)

Searches the NRWE court database and extracts case metadata:

- **Input**: Date range (configured in `main.py`)
- **Process**: 
  - Automates web browser to navigate search forms
  - Sets search criteria (court type, jurisdiction, decision type)
  - Iterates through result pages to collect case links
- **Output**: JSON Lines files in `data/ids/` containing case metadata

**Configuration options:**
- Court type: Oberlandesgericht (Higher Regional Court)
- Jurisdiction: Ordentliche Gerichtsbarkeit (Ordinary jurisdiction)
- Decision type: Urteil (Judgment)

#### Stage 2: Document Download (`download_docs`)

Downloads full HTML documents for each case:

- **Input**: Case metadata from Stage 1
- **Process**:
  - Validates and filters URLs
  - Downloads HTML documents concurrently (4 concurrent downloads)
  - Implements retry logic for failed downloads
  - Skips already downloaded files
- **Output**: HTML files stored in `data/docs/nrwe/olgs/`

**Features:**
- URL validation (must be absolute, HTTPS, .html extension)
- Concurrent downloading with semaphore-based rate limiting
- Automatic retry with exponential backoff
- Content-type verification

#### Stage 3: Document Parsing (`parse_docs`)

Extracts structured data from HTML documents:

- **Input**: Downloaded HTML files
- **Process**:
  - Parses HTML structure to identify document sections
  - Extracts metadata (date, court, case number, etc.)
  - Identifies and parses verdict text using regex patterns
  - Handles multiple document formats
- **Output**: Structured data in `data/parsed_docs.jsonl`

**Supported sections:**
- **Meta**: Court information, dates, case numbers
- **Leitsätze**: Legal principles, keywords, subject areas
- **Tenor**: Decision summary
- **Verdict**: Full reasoning with two supported formats

## Data Structure

### Scraped Metadata (Stage 1)
```json
{
  "datetime": "2024-01-15T10:30:00Z",
  "page": 1,
  "text": "Case title and basic info",
  "href": "https://www.justiz.nrw/nrwe/olgs/..."
}
```

### Parsed Document (Stage 3)
```json
{
  "datum": "15.01.2024",
  "gericht": "OLG Düsseldorf",
  "aktenzeichen": "I-1 U 123/23",
  "ecli": "ECLI:DE:OLGD:2024:0115.I1U123.23.00",
  "format": "FORMAT_1",
  "tatbestand": "Facts of the case...",
  "entscheidungsgründe": "Legal reasoning...",
  "verdict_html": "<div class=\"maindiv\">..."
}
```

## Configuration

### Date Range

Edit `main.py` to modify the scraping date range:

```python
START_DATE = datetime(year=2020, month=1, day=1)
END_DATE = datetime(year=2024, month=12, day=31)
```

### Concurrency Settings

Modify `src/download_docs.py` to adjust download concurrency:

```python
CONCURRENCY = 4  # Number of concurrent downloads
TIMEOUT = 60     # Request timeout in seconds
```

### WebDriver Settings

Update `src/run_scraping.py` for browser configuration:

```python
WEBDRIVER_WAIT_TIMEOUT = 60    # Element wait timeout
SLEEP_TIME_PAGINATION = 1      # Delay between pages
```

## File Structure

```
nrwe-scraper/
├── main.py                    # Main entry point
├── requirements.txt           # Python dependencies
├── README.md                 # This file
├── edgedriver_win64/         # WebDriver executable
│   └── msedgedriver.exe
├── src/                      # Source code
│   ├── utils.py             # Shared utilities and constants
│   ├── run_scraping.py      # Web scraping module
│   ├── download_docs.py     # Document download module
│   ├── extract_verdict.py   # Verdict text extraction
│   └── parse_docs.py        # HTML parsing module
└── data/                     # Generated data
    ├── ids/                 # Scraped case metadata
    ├── docs/                # Downloaded HTML files
    └── parsed_docs.jsonl    # Final structured data
```

## Troubleshooting

### Common Issues

**WebDriver Not Found**
```
FileNotFoundError: Executable not found at edgedriver_win64/msedgedriver.exe
```
- Ensure Edge WebDriver is downloaded and placed in the correct directory
- Verify the WebDriver version matches your Edge browser version

**Connection Timeouts**
```
TimeoutException: Element not found
```
- Check your internet connection
- The court website may be temporarily unavailable
- Increase `WEBDRIVER_WAIT_TIMEOUT` in `run_scraping.py`

**Download Failures**
```
HTTPError: 403 Forbidden
```
- The website may be blocking requests
- Check if the court website structure has changed
- Verify the User-Agent headers in `src/utils.py`

**Parsing Errors**
```
Multiple div types identified
```
- The HTML structure of court documents may have changed
- Review the parsing logic in `parse_docs.py`
- Check the XPath selectors for accuracy

### Logging

The scraper uses Python's logging module. To see detailed logs:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Resume Interrupted Scraping

The scraper automatically skips:
- Date ranges already processed (existing files in `data/ids/`)
- Documents already downloaded (existing files in `data/docs/`)

To force re-processing, delete the relevant output files.

## Legal Considerations

This scraper is designed for research and educational purposes. When using this tool:

- Respect the website's terms of service
- Don't overwhelm the server with excessive requests
- Be mindful of copyright and data protection laws
- Use the scraped data responsibly and ethically

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is provided for educational and research purposes. Please ensure compliance with applicable laws and the target website's terms of service.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the error logs for specific error messages
3. Verify your setup matches the installation requirements
4. Open an issue with detailed error information and system details