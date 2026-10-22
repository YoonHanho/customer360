"""Load and validate the synthetic CSV data contract."""

from pathlib import Path

import pandas as pd

from harness.schema import REQUIRED_COLUMNS


def load_data(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Load all required CSVs; fail loudly if files or required columns are missing."""
    datasets: dict[str, pd.DataFrame] = {}
    for name, required in REQUIRED_COLUMNS.items():
        path = data_dir / f"{name}.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Required mock dataset is missing: {path}")
        frame = pd.read_csv(path)
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{path.name} is missing required columns: {', '.join(sorted(missing))}")
        datasets[name] = frame
    if datasets["customers"]["customer_id"].duplicated().any():
        raise ValueError("customers.csv contains duplicate customer_id values")
    return datasets
