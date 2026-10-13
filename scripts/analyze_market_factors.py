
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scripts.common import (
    PROCESSED_DIR, REPORTS_DIR, ensure_dirs
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def main():
    ensure_dirs()

    source = PROCESSED_DIR / "master_market_dataset.csv"

    if not source.exists():
        raise FileNotFoundError(
            "Run build_master_dataset.py first."
        )

    df = pd.read_csv(source, parse_dates=["date"])
    df = df.sort_values(["symbol", "date"])

    df["daily_return"] = pd.to_numeric(
        df["daily_return"], errors="coerce"
    )

    factors = {
        "S&P 500 return": "sp500_return",
        "Nasdaq return": "nasdaq_return",
        "VIX daily change": "vix_change",
        "Treasury 10Y yield proxy": "us_10y_treasury_yield_proxy",
        "US dollar index": "us_dollar_index",
        "Federal funds rate": "federal_funds_rate",
        "CPI": "consumer_price_index",
        "Unemployment": "unemployment_rate",
        "FRED 10Y yield": "treasury_10y_yield",
        "Real GDP": "real_gdp",
    }

    results = []

    for symbol, group in df.groupby("symbol"):
        for factor_name, col in factors.items():
            if col not in group.columns:
                continue

            x = pd.to_numeric(group[col], errors="coerce")

            # Convert index/yield proxies to changes.
            if factor_name in [
                "Treasury 10Y yield proxy", "US dollar index"
            ]:
                x = x.pct_change()

            # Changes in economic indicators rather than raw levels.
            elif factor_name in [
                "Federal funds rate", "CPI", "Unemployment",
                "FRED 10Y yield", "Real GDP"
            ]:
                x = x.diff()

            pairs = pd.DataFrame({
                "stock_return": group["daily_return"],
                "factor": x,
            })

            pairs = pairs.replace(
                [np.inf, -np.inf], np.nan
            ).dropna()

            if len(pairs) < 20 or pairs["factor"].nunique() < 2:
                continue

            correlation = pairs["stock_return"].corr(
                pairs["factor"]
            )

            # Simple ordinary least squares regression:
            # stock return = intercept + beta * factor
            X = np.column_stack([
                np.ones(len(pairs)),
                pairs["factor"].to_numpy(),
            ])
            y = pairs["stock_return"].to_numpy()

            coefficients = np.linalg.lstsq(
                X, y, rcond=None
            )[0]

            predictions = X @ coefficients
            ss_total = ((y - y.mean()) ** 2).sum()
            ss_residual = ((y - predictions) ** 2).sum()

            r_squared = (
                1 - ss_residual / ss_total
                if ss_total > 0 else np.nan
            )

            results.append({
                "symbol": symbol,
                "factor": factor_name,
                "observations": len(pairs),
                "correlation": correlation,
                "simple_ols_beta": coefficients[1],
                "r_squared": r_squared,
            })

    results_df = pd.DataFrame(results)

    results_df.to_csv(
        REPORTS_DIR / "factor_relationships.csv",
        index=False,
    )

    if not results_df.empty:
        results_df.sort_values(
            ["symbol", "correlation"],
            ascending=[True, False],
        ).to_csv(
            REPORTS_DIR / "factor_relationships_sorted.csv",
            index=False,
        )

        for symbol, group in results_df.groupby("symbol"):
            plot_data = group.sort_values("correlation")

            plt.figure(figsize=(10, 5))
            plt.barh(
                plot_data["factor"],
                plot_data["correlation"],
            )
            plt.axvline(0, linewidth=1)
            plt.title(
                f"{symbol}: factor correlation with daily returns"
            )
            plt.xlabel("Correlation (-1 to +1)")
            plt.tight_layout()

            plt.savefig(
                REPORTS_DIR / f"{symbol.lower()}_factor_correlations.png",
                dpi=150,
            )
            plt.close()

        logging.info(
            "Factor analysis saved to %s",
            REPORTS_DIR,
        )
    else:
        logging.warning(
            "No factor results found. Check market downloads "
            "and whether the master dataset includes indicator columns."
        )


if __name__ == "__main__":
    main()
