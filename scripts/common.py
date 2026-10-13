
from pathlib import Path
from datetime import date, timedelta
import os
import json


# ============================================================
# PROJECT PATHS
# ============================================================

# Project root:
# C:\Users\vasup\PycharmProjects\Stock_Market_Intelligence
PROJECT_DIR = Path(__file__).resolve().parents[1]

# Main data directory
DATA_DIR = PROJECT_DIR / "data"

# Raw downloaded data
RAW_DIR = DATA_DIR / "raw"
STOCK_RAW_DIR = RAW_DIR / "stock_prices"
MARKET_RAW_DIR = RAW_DIR / "market_indicators"
ECON_RAW_DIR = RAW_DIR / "economic_data"

# Processed datasets
PROCESSED_DIR = DATA_DIR / "processed"

# Engineered features
FEATURES_DIR = DATA_DIR / "features"

# Download status and metadata
METADATA_DIR = DATA_DIR / "metadata"

# Analysis reports and charts
REPORTS_DIR = DATA_DIR / "reports"


# ============================================================
# CONFIGURATION
# ============================================================

# Stocks to analyze
SYMBOLS = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "GOOGL",
]

# Rolling historical window in calendar days
CALENDAR_DAYS = 500


# ============================================================
# CREATE REQUIRED DIRECTORIES
# ============================================================

def ensure_dirs():
    """
    Create all required project data directories.
    Existing folders are preserved.
    """

    directories = [
        DATA_DIR,
        RAW_DIR,
        STOCK_RAW_DIR,
        MARKET_RAW_DIR,
        ECON_RAW_DIR,
        PROCESSED_DIR,
        FEATURES_DIR,
        METADATA_DIR,
        REPORTS_DIR,
    ]

    for directory in directories:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )


# ============================================================
# DATE WINDOW
# ============================================================

def date_window():
    """
    Return the rolling historical date range.

    Start date:
        Today minus CALENDAR_DAYS.

    End date:
        Tomorrow, because many data providers treat the
        requested end date as exclusive.
    """

    today = date.today()

    start_date = today - timedelta(
        days=CALENDAR_DAYS
    )

    end_date = today + timedelta(
        days=1
    )

    return start_date, end_date


# ============================================================
# JSON OUTPUT
# ============================================================

def write_json(data, path):
    """
    Save data to a JSON file.

    Existing files are overwritten.
    Parent directories are created automatically.
    """

    output_path = Path(path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            default=str,
            ensure_ascii=False,
        )


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

def read_env_value(name):
    """
    Read a configuration value from:
    1. System environment variables.
    2. A .env file in the project root.

    System environment variables take priority.
    """

    # First, check system environment variables.
    value = os.getenv(name)

    if value:
        return value.strip()

    # Otherwise, look for a .env file.
    env_file = PROJECT_DIR / ".env"

    if not env_file.exists():
        return None

    for line in env_file.read_text(
        encoding="utf-8"
    ).splitlines():

        line = line.strip()

        # Ignore blank lines and comments.
        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        if key.strip() == name:
            return value.strip().strip('"').strip("'")

    return None


# ============================================================
# CONFIGURATION CHECK
# ============================================================

if __name__ == "__main__":
    ensure_dirs()

    start_date, end_date = date_window()

    print("=" * 55)
    print("STOCK MARKET INTELLIGENCE CONFIGURATION")
    print("=" * 55)

    print(f"Project directory : {PROJECT_DIR}")
    print(f"Data directory    : {DATA_DIR}")
    print(f"Raw data          : {RAW_DIR}")
    print(f"Stock data        : {STOCK_RAW_DIR}")
    print(f"Market indicators : {MARKET_RAW_DIR}")
    print(f"Economic data     : {ECON_RAW_DIR}")
    print(f"Processed data    : {PROCESSED_DIR}")
    print(f"Features          : {FEATURES_DIR}")
    print(f"Metadata          : {METADATA_DIR}")
    print(f"Reports           : {REPORTS_DIR}")

    print(f"Historical start  : {start_date}")
    print(f"Historical end    : {end_date}")

    print(f"Stock symbols     : {', '.join(SYMBOLS)}")

    print("=" * 55)
    print("Configuration loaded successfully.")
