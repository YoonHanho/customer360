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
        frame = pd.read_csv(
            path,
            encoding="utf-8-sig",
            dtype={"고객번호": "string"},
        )
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{path.name} is missing required columns: {', '.join(sorted(missing))}")
        datasets[name] = frame
    if datasets["고객"]["고객번호"].duplicated().any():
        raise ValueError("고객.csv contains duplicate 고객번호 values")
    customer_ids = set(datasets["고객"]["고객번호"].astype(str))
    for name, frame in datasets.items():
        if name == "고객":
            continue
        references = set(frame["고객번호"].dropna().astype(str))
        if not references.issubset(customer_ids):
            raise ValueError(f"{name}.csv contains unknown 고객번호 values")
    nba = datasets["NBA"].copy()
    nba["제안순서"] = pd.to_numeric(nba["제안순서"], errors="raise")
    for customer_id, proposals in nba.groupby("고객번호"):
        if sorted(proposals["제안순서"].tolist()) != [1, 2, 3]:
            raise ValueError(
                f"NBA.csv must contain proposal orders 1, 2, and 3 for {customer_id}"
            )
    return datasets
