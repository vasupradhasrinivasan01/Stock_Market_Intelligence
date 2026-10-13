
import logging
import requests
import pandas as pd

from scripts.common import (
    ECON_RAW_DIR, METADATA_DIR, ensure_dirs,
    date_window, read_env_value, write_json
)

SERIES = {
    "FEDFUNDS": "federal_funds_rate",
    "CPIAUCSL": "consumer_price_index",
    "UNRATE": "unemployment_rate",
    "DGS10": "treasury_10y_yield",
    "GDPC1": "real_gdp",
}

API_URL = "https://api.stlouisfed.org/fred/series/observations"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def main():
    ensure_dirs()
    api_key = read_env_value("FRED_API_KEY")

    if not api_key:
        logging.warning(
            "FRED_API_KEY is not configured. Skipping economic data."
        )
        return

    start, end = date_window()
    status = {}

    for series_id, name in SERIES.items():
        try:
            logging.info("Downloading %s...", name)

            response = requests.get(
                API_URL,
                params={
                    "api_key": api_key,
                    "file_type": "json",
                    "series_id": series_id,
                    "observation_start": start.isoformat(),
                    "observation_end": (end - pd.Timedelta(days=1)).isoformat(),
                },
                timeout=30,
            )
            response.raise_for_status()

            df = pd.DataFrame(
                response.json().get("observations", [])
            )

            if df.empty:
                raise RuntimeError("No observations returned")

            df = df[["date", "value"]].copy()
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df = df.dropna(subset=["date"]).sort_values("date")

            output_path = ECON_RAW_DIR / f"{name}.csv"
            df.to_csv(output_path, index=False)

            status[name] = {"success": True, "rows": len(df)}
            logging.info("%s: saved %s observations", name, len(df))

        except Exception as exc:
            status[name] = {"success": False, "error": str(exc)}
            logging.exception("Failed FRED series %s", series_id)

    write_json(status, METADATA_DIR / "fred_download_status.json")


if __name__ == "__main__":
    main()
