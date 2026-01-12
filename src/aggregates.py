# src/aggregates.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pandas as pd


@dataclass
class TopActionsStore:
    processed_dir: Path

    def __post_init__(self) -> None:
        self.processed_dir = Path(self.processed_dir)

        self._by_country = self._load_csv("top4_next_actions_by_country.csv")
        self._by_solution = self._load_csv("top4_next_actions_by_solution.csv")
        self._by_country_solution = self._load_csv("top4_next_actions_by_country_solution.csv")

        # توحيد نوع الأعمدة
        for col in ["Country", "solution", "next_action"]:
            if col in self._by_country.columns:
                self._by_country[col] = self._by_country[col].astype(str)
            if col in self._by_solution.columns:
                self._by_solution[col] = self._by_solution[col].astype(str)
            if col in self._by_country_solution.columns:
                self._by_country_solution[col] = self._by_country_solution[col].astype(str)

    def _load_csv(self, name: str) -> pd.DataFrame:
        path = self.processed_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Missing required file: {path}")
        return pd.read_csv(path)

    def top4_by_country(self, country: str) -> pd.DataFrame:
        df = self._by_country[self._by_country["Country"] == str(country)]
        return df.sort_values("count", ascending=False).head(4).reset_index(drop=True)

    def top4_by_solution(self, solution: str) -> pd.DataFrame:
        df = self._by_solution[self._by_solution["solution"] == str(solution)]
        return df.sort_values("count", ascending=False).head(4).reset_index(drop=True)

    def top4_by_country_solution(self, country: str, solution: str) -> pd.DataFrame:
        df = self._by_country_solution[
            (self._by_country_solution["Country"] == str(country)) &
            (self._by_country_solution["solution"] == str(solution))
        ]
        return df.sort_values("count", ascending=False).head(4).reset_index(drop=True)
