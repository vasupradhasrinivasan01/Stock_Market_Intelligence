
from scripts.download_history import main as download_stocks
from scripts.download_market_indicators import main as download_markets
from scripts.download_fred_data import main as download_economic
from scripts.build_master_dataset import main as build_dataset
from scripts.analyze_market_factors import main as analyze_factors


def run_step(label, function):
    print("\n" + "=" * 65)
    print(label)
    print("=" * 65)
    function()


if __name__ == "__main__":
    run_step("1/5 Download stock history", download_stocks)
    run_step("2/5 Download market indicators", download_markets)
    run_step("3/5 Download economic data (optional)", download_economic)
    run_step("4/5 Build master dataset", build_dataset)
    run_step("5/5 Analyze market factors", analyze_factors)

    print("\nPipeline finished. Check the data/ folder.")
