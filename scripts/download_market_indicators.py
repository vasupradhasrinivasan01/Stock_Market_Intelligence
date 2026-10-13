
import logging
import pandas as pd
import yfinance as yf

from scripts.common import (
    MARKET_RAW_DIR,
    PROCESSED_DIR,
    METADATA_DIR,
    ensure_dirs,
    date_window,
    write_json,
)

# Market indicators to download.
TICKERS = {
    "^GSPC": "sp500",
    "^IXIC": "nasdaq_composite",
    "^VIX": "vix",
    "^TNX": "us_10y_treasury_yield_proxy",
    "DX-Y.NYB": "us_dollar_index",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


def download_indicator(ticker, indicator_name, start, end):
    """Download one indicator and standardize its columns."""

    df = yf.download(
        ticker,
        start=start.isoformat(),
        end=end.isoformat(),
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if df is None or df.empty:
        raise RuntimeError(f"No data returned for {ticker}")

    # Handle yfinance MultiIndex columns.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(column[0]) for column in df.columns]

    df = df.reset_index()

    # Standardize column names.
    df.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in df.columns
    ]

    if "date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "date"})

    # Normalize dates to timezone-naive timestamps.
    df["date"] = (
        pd.to_datetime(df["date"], utc=True)
        .dt.tz_convert(None)
        .dt.normalize()
    )

    # Ensure expected columns exist.
    for column in [
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
    ]:
        if column not in df.columns:
            df[column] = pd.NA

    df["ticker"] = ticker
    df["indicator"] = indicator_name

    columns = [
        "date",
        "ticker",
        "indicator",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
    ]

    return df[columns].sort_values("date").reset_index(drop=True)


def main():
    """Download all market indicators and save combined datasets."""

    ensure_dirs()

    start, end = date_window()

    logging.info(
        "Market indicator window: %s to %s",
        start,
        end - pd.Timedelta(days=1),
    )

    downloaded_frames = []
    status = {}

    for ticker, indicator_name in TICKERS.items():
        try:
            logging.info(
                "Downloading %s (%s)...",
                indicator_name,
                ticker,
            )

            df = download_indicator(
                ticker=ticker,
                indicator_name=indicator_name,
                start=start,
                end=end,
            )

            # Save individual indicator CSV.
            individual_path = (
                MARKET_RAW_DIR / f"{indicator_name}.csv"
            )
            df.to_csv(individual_path, index=False)

            downloaded_frames.append(df)

            status[indicator_name] = {
                "ticker": ticker,
                "success": True,
                "rows": len(df),
                "file": str(individual_path),
            }

            logging.info(
                "%s: saved %s rows",
                indicator_name,
                len(df),
            )

        except Exception as exc:
            status[indicator_name] = {
                "ticker": ticker,
                "success": False,
                "error": str(exc),
            }

            logging.exception(
                "Failed to download %s",
                indicator_name,
            )

    if not downloaded_frames:
        write_json(
            status,
            METADATA_DIR / "market_download_status.json",
        )
        raise RuntimeError(
            "All market indicator downloads failed. "
            "Check your internet connection and ticker availability."
        )

    # Combine indicator records into one long-format dataset.
    combined = pd.concat(
        downloaded_frames,
        ignore_index=True,
    ).sort_values(["date", "indicator"])

    combined_csv = MARKET_RAW_DIR / "all_market_indicators.csv"
    combined_json = MARKET_RAW_DIR / "all_market_indicators.json"

    combined.to_csv(combined_csv, index=False)

    combined.to_json(
        combined_json,
        orient="records",
        date_format="iso",
        indent=2,
    )

    # Create a wide-format dataset with one column per indicator.
    wide = combined.pivot_table(
        index="date",
        columns="indicator",
        values="close",
        aggfunc="last",
    ).reset_index()

    wide.columns.name = None

    wide_csv = PROCESSED_DIR / "market_indicators.csv"
    wide_json = PROCESSED_DIR / "market_indicators.json"

    wide.to_csv(wide_csv, index=False)

    wide.to_json(
        wide_json,
        orient="records",
        date_format="iso",
        indent=2,
    )

    # Save download status for troubleshooting.
    write_json(
        {
            "start_date": str(start),
            "end_date_inclusive": str(end - pd.Timedelta(days=1)),
            "indicators": status,
            "successful_indicators": len(downloaded_frames),
            "total_indicators": len(TICKERS),
            "combined_rows": len(combined),
        },
        METADATA_DIR / "market_download_status.json",
    )

    logging.info("=" * 50)
    logging.info("MARKET INDICATOR DOWNLOAD COMPLETED")
    logging.info("Raw data: %s", MARKET_RAW_DIR)
    logging.info("Combined data: %s", combined_csv)
    logging.info("Download status: %s", METADATA_DIR)
    logging.info("=" * 50)


if __name__ == "__main__":
    main()
