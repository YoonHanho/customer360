"""Export an offline dashboard using CSV files from data_real/."""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path

from harness.data_loader import load_data


ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = ROOT / "data_real"
DEFAULT_OUTPUT_PATH = ROOT / "customer360_real_offline.html"
DATASET_GLOBALS = {
    "고객": "CUSTOMERS",
    "잔고추이": "BALANCE_TREND",
    "자산비중": "ASSET_ALLOCATION",
    "보유상품": "HOLDINGS",
    "거래금액": "TRANSACTION_AMOUNTS",
    "투자수익률": "INVESTMENT_RETURNS",
    "회전율": "TURNOVER",
    "앱접속일수": "APP_LOGINS",
    "앱메뉴TOP": "APP_MENU_TOP",
    "검색어": "SEARCH_TERMS",
    "챗봇상담": "CHATBOT_CONSULTATIONS",
    "고객센터상담": "CALL_CENTER_CONSULTATIONS",
    "예측": "PREDICTIONS",
    "NBA": "NBA",
}


def generate_real_html(
    data_dir: Path = DEFAULT_DATA_DIR,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """Validate real CSVs, use them for the existing exporter, and restore state."""
    data_dir = Path(data_dir).expanduser().resolve()
    output_path = Path(output_path).expanduser().resolve()
    datasets = load_data(data_dir)

    import harness.data_loader as data_loader

    original_loader = data_loader.load_data

    def load_selected_data(_data_dir: Path):
        del _data_dir
        return datasets

    data_loader.load_data = load_selected_data
    try:
        dashboard = importlib.import_module("pages.scr002_customer360")
        exporter = importlib.import_module("export_html")
    finally:
        data_loader.load_data = original_loader

    original_dashboard_data = dashboard.DATA
    original_dashboard_globals = {
        global_name: getattr(dashboard, global_name)
        for global_name in DATASET_GLOBALS.values()
    }
    original_exporter_customers = exporter.CUSTOMERS
    try:
        dashboard.DATA = datasets
        for dataset_name, global_name in DATASET_GLOBALS.items():
            setattr(dashboard, global_name, datasets[dataset_name])
        exporter.CUSTOMERS = datasets["고객"]
        return exporter.export_html(output_path)
    finally:
        dashboard.DATA = original_dashboard_data
        for global_name, original_value in original_dashboard_globals.items():
            setattr(dashboard, global_name, original_value)
        exporter.CUSTOMERS = original_exporter_customers


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create an offline dashboard from the CSV files in data_real/."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Folder containing the 14 real-data CSV files (default: data_real)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output HTML path (default: customer360_real_offline.html)",
    )
    arguments = parser.parse_args()
    output_path = generate_real_html(arguments.data_dir, arguments.output)
    print(f"Real-data offline dashboard created: {output_path}")


if __name__ == "__main__":
    main()
