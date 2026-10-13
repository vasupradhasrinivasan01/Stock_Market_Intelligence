
import logging
import pandas as pd
import yfinance as yf

from scripts.common import (
    SYMBOLS,
    STOCK_RAW_DIR,
    PROCESSED_DIR,
    METADATA_DIR,
    ensure_dirs,
    date_window,
    write_json,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


def download_stock(symbol, start_date, end_date):
    """Download historical data for one stock."""

    df = yf.download(
        symbol,
        start=start_date.isoformat(),
        end=end_date.isoformat(),
        interval="1d",
        auto_adjust=False,
        actions=True,
        progress=False,
        threads=False,
    )

    if df is None or df.empty:
        raise RuntimeError(f"No data returned for {symbol}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(col[0]) for col in df.columns]

    df = df.reset_index()

    df.columns = [
        str(col).strip().lower().replace(" ", "_")
        for col in df.columns
    ]

    if "date" not in df.columns:
        df.rename(columns={df.columns[0]: "date"}, inplace=True)

    df["date"] = (
        pd.to_datetime(df["date"], utc=True)
        .dt.tz_convert(None)
        .dt.normalize()
    )

    df["symbol"] = symbol

    for col in [
        "open", "high", "low", "close", "adj_close",
        "volume", "dividends", "stock_splits"
    ]:
        if col not in df.columns:
            df[col] = 0 if col in ["dividends", "stock_splits"] else pd.NA

    return df[
        [
            "date", "symbol", "open", "high", "low", "close",
            "adj_close", "volume", "dividends", "stock_splits"
        ]
    ].sort_values("date")


def main():
    ensure_dirs()

    start_date, end_date = date_window()

    logging.info(
        "Downloading stock history from %s to %s",
        start_date,
        end_date - pd.Timedelta(days=1),
    )

    frames = []
    status = {}

    for symbol in SYMBOLS:
        try:
            logging.info("Downloading %s...", symbol)

            df = download_stock(symbol, start_date, end_date)

            # Keep one raw CSV per ticker if you want individual backups.
            # Delete these two lines if you want ONLY the combined dataset.
            df.to_csv(STOCK_RAW_DIR / f"{symbol}.csv", index=False)

            frames.append(df)

            status[symbol] = {
                "success": True,
                "rows": len(df),
            }

            logging.info("%s: downloaded %s rows", symbol, len(df))

        except Exception as exc:
            status[symbol] = {
                "success": False,
                "error": str(exc),
            }
            logging.exception("Failed to download %s", symbol)

    if not frames:
        raise RuntimeError("No stock data downloaded successfully.")

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["date", "symbol"])

    # All stocks combined into one file.
    csv_path = PROCESSED_DIR / "market_indicators.csv"
    json_path = PROCESSED_DIR / "market_indicators.json"
    excel_path = PROCESSED_DIR / "market_indicators.xlsx"

    # Overwrite existing files each run.
    combined.to_csv(csv_path, index=False)

    combined.to_json(
        json_path,
        orient="records",
        date_format="iso",
        indent=2,
    )

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        combined.to_excel(
            writer,
            sheet_name="All Stocks",
            index=False,
        )

        for symbol, group in combined.groupby("symbol"):
            group.to_excel(
                writer,
                sheet_name=symbol,
                index=False,
            )

    write_json(
        {
            "start_date": str(start_date),
            "end_date_exclusive": str(end_date),
            "stocks": status,
            "total_rows": len(combined),
            "output_files": [
                str(csv_path),
                str(json_path),
                str(excel_path),
            ],
        },
        METADATA_DIR / "stock_download_status.json",
    )

    logging.info("=" * 55)
    logging.info("STOCK DOWNLOAD COMPLETED")
    logging.info("Total rows: %s", len(combined))
    logging.info("CSV: %s", csv_path)
    logging.info("JSON: %s", json_path)
    logging.info("Excel: %s", excel_path)
    logging.info("=" * 55)


if __name__ == "__main__":
    main()
