
import logging
import pandas as pd

from scripts.common import (
    STOCK_RAW_DIR, ECON_RAW_DIR, PROCESSED_DIR,
    FEATURES_DIR, ensure_dirs
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def main():
    ensure_dirs()

    stock_files = sorted(STOCK_RAW_DIR.glob("*.csv"))
    if not stock_files:
        raise FileNotFoundError(
            "No stock CSV files found. Run download_history first."
        )

    stocks = pd.concat(
        [pd.read_csv(path, parse_dates=["date"]) for path in stock_files],
        ignore_index=True,
    )

    stocks["date"] = (
        pd.to_datetime(stocks["date"], errors="coerce")
        .dt.tz_localize(None)
        .dt.normalize()
    )

    stocks = (
        stocks.dropna(subset=["date", "symbol"])
        .drop_duplicates(["date", "symbol"])
    )

    # Merge the broad market indicators.
    market_path = PROCESSED_DIR / "market_indicators.csv"

    if market_path.exists():
        market = pd.read_csv(market_path, parse_dates=["date"])
        market["date"] = pd.to_datetime(market["date"]).dt.normalize()

        stocks = stocks.merge(market, on="date", how="left")
    else:
        logging.warning("Market indicators file not found.")

    # Merge economic series using the latest observation on or
    # before each trading date.
    for path in sorted(ECON_RAW_DIR.glob("*.csv")):
        econ = pd.read_csv(path, parse_dates=["date"])

        if not {"date", "value"}.issubset(econ.columns):
            continue

        name = path.stem
        econ["date"] = pd.to_datetime(econ["date"]).dt.normalize()
        econ = (
            econ.dropna(subset=["date"])
            .sort_values("date")
            .rename(columns={"value": name})
        )

        stocks = pd.merge_asof(
            stocks.sort_values("date"),
            econ[["date", name]].sort_values("date"),
            on="date",
            direction="backward",
        )

    stocks = stocks.sort_values(
        ["symbol", "date"]
    ).reset_index(drop=True)

    price_col = (
        "adj_close" if "adj_close" in stocks.columns else "close"
    )
    stocks["analysis_price"] = pd.to_numeric(
        stocks[price_col], errors="coerce"
    )

    prices = stocks.groupby("symbol")["analysis_price"]

    stocks["daily_return"] = prices.pct_change()
    stocks["return_5d"] = prices.pct_change(5)
    stocks["return_20d"] = prices.pct_change(20)

    stocks["moving_average_20"] = prices.transform(
        lambda x: x.rolling(20, min_periods=10).mean()
    )
    stocks["moving_average_50"] = prices.transform(
        lambda x: x.rolling(50, min_periods=20).mean()
    )
    stocks["volatility_20d"] = stocks.groupby("symbol")[
        "daily_return"
    ].transform(
        lambda x: x.rolling(20, min_periods=10).std()
    )

    # Broad market daily changes.
    for col, new_col in [
        ("sp500", "sp500_return"),
        ("nasdaq_composite", "nasdaq_return"),
        ("vix", "vix_change"),
    ]:
        if col in stocks.columns:
            stocks[new_col] = (
                stocks.groupby("symbol")[col]
                .transform(lambda x: pd.to_numeric(x, errors="coerce").pct_change())
            )

    csv_path = PROCESSED_DIR / "master_market_dataset.csv"
    json_path = PROCESSED_DIR / "master_market_dataset.json"

    stocks.to_csv(csv_path, index=False)
    stocks.to_json(
        json_path, orient="records", date_format="iso", indent=2
    )

    stocks.to_csv(
        FEATURES_DIR / "market_analysis_features.csv", index=False
    )
    stocks.to_json(
        FEATURES_DIR / "market_analysis_features.json",
        orient="records", date_format="iso", indent=2
    )

    logging.info(
        "Master dataset saved: %s rows, %s columns",
        len(stocks), len(stocks.columns)
    )
    logging.info("Output: %s", csv_path)


if __name__ == "__main__":
    main()
