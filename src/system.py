# src/system.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

import pandas as pd

from .aggregates import TopActionsStore
from .weights import AccountWeightStore, update_account_weight, DEFAULT_BASE_WEIGHTS


@dataclass
class CustomerJourneySystem:
    """
    Step 4 (Build a complete system) وفق نص المسألة:
      - عند إضافة معلومات الحساب: إرجاع Top4 by country / solution / country+solution
      - عند إضافة action: إعادة حساب Top4 باستخدام الأوزان الجديدة (Dynamic Weight Adjustment)
    """
    processed_dir: Path

    def __post_init__(self) -> None:
        # تحميل جداول Top4 من data/processed
        self.store = TopActionsStore(self.processed_dir)

        # تخزين حالة الأوزان لكل حساب (MVP: JSON)
        self.weight_store = AccountWeightStore(Path(self.processed_dir) / "account_state.json")

        # Base weights الافتراضية (يمكن تعديلها لاحقاً)
        self.base_weights = DEFAULT_BASE_WEIGHTS

    def add_account(self, account_id: str, country: str, solution: str) -> Dict[str, Any]:
        """
        عند إضافة معلومات الحساب، الإخراج يجب أن يكون:
          - Top 4 actions by country
          - Top 4 actions by solution
          - Top 4 actions by country and solution
        """
        by_country = self.store.top4_by_country(country)
        by_solution = self.store.top4_by_solution(solution)
        by_country_solution = self.store.top4_by_country_solution(country, solution)

        return {
            "account_id": str(account_id),
            "country": str(country),
            "solution": str(solution),
            "top4_by_country": by_country.to_dict(orient="records"),
            "top4_by_solution": by_solution.to_dict(orient="records"),
            "top4_by_country_solution": by_country_solution.to_dict(orient="records"),
        }

    def add_action(self, account_id: str, country: str, solution: str, action_type: str) -> Dict[str, Any]:
        """
        عند إضافة action، يجب إعادة حساب Top4 باستخدام الأوزان الجديدة.

        تطبيق MVP مطابق للصورة:
          - First touch: adjusted = base_weight(action_type)
          - Non-first touch: adjusted = base_weight(action_type) * (1 - last_touch_weight)

        ثم إعادة ترتيب Top4 للـ (country / solution / country+solution) باستخدام:
          score = count * base_weight(candidate) * adjusted_weight
        """
        adjusted_weight = update_account_weight(
            store=self.weight_store,
            account_id=account_id,
            action_type=action_type,
            base_weights=self.base_weights,
        )

        # القوائم الأساسية (قبل إعادة الترتيب)
        by_country = self.store.top4_by_country(country)
        by_solution = self.store.top4_by_solution(solution)
        by_country_solution = self.store.top4_by_country_solution(country, solution)

        def rerank(df_top: pd.DataFrame) -> pd.DataFrame:
            if df_top is None or df_top.empty:
                return df_top

            df_top = df_top.copy()

            # وزن أساسي لكل مرشح
            df_top["base_weight"] = df_top["next_action"].map(lambda a: float(self.base_weights.get(a, 1.0)))

            # إعادة حساب score بالأوزان الجديدة (MVP)
            df_top["score"] = df_top["count"].astype(float) * df_top["base_weight"] * float(adjusted_weight)

            return df_top.sort_values("score", ascending=False).head(4).reset_index(drop=True)

        out_country = rerank(by_country)
        out_solution = rerank(by_solution)
        out_cs = rerank(by_country_solution)

        return {
            "account_id": str(account_id),
            "country": str(country),
            "solution": str(solution),
            "added_action": str(action_type),
            "adjusted_weight": float(adjusted_weight),
            "top4_by_country": out_country.to_dict(orient="records") if out_country is not None else [],
            "top4_by_solution": out_solution.to_dict(orient="records") if out_solution is not None else [],
            "top4_by_country_solution": out_cs.to_dict(orient="records") if out_cs is not None else [],
        }
