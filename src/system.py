# src/system.py
#""

system.py

هذا الملف يحتوي على تعريف نظامCustomerJourneySystem  المسؤول عن:
- تحميل بيانات المسارات (journeys) من الملفات المعالجة
- حفظ حالة كل حساب (Account state) أثناء تنفيذ الإجراءات
- حساب أفضل 4 إجراءات مقترحة لكل حساب بناءً على الدولة والحل (Country, Solution)""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

import pandas as pd

from .aggregates import TopActionsStore
from .weights import (
    AccountWeightStore,
    update_account_weight,
    DEFAULT_BASE_WEIGHTS,
)


@dataclass
class CustomerJourneySystem:
    """
    Step 4 – Build a complete system:

    - add_account:
        * Top 4 actions by country
        * Top 4 actions by solution
        * Top 4 actions by country and solution

    - add_action:
        * إعادة حساب Top 4 باستخدام الأوزان الجديدة
          (Dynamic Weight Adjustment)
    """
    processed_dir: Path

    def __post_init__(self) -> None:
        # تحميل التجميعات
        self.store = TopActionsStore(self.processed_dir)

        # تخزين حالة الحسابات (last touch weights)
        self.weight_store = AccountWeightStore(
            Path(self.processed_dir) / "account_state.json"
        )

        # Base weights الافتراضية
        self.base_weights = DEFAULT_BASE_WEIGHTS

    # ------------------------------------------------------------------
    # ADD ACCOUNT
    # ------------------------------------------------------------------
    def add_account(self, account_id: str, country: str, solution: str) -> Dict[str, Any]:
        """
        عند إضافة معلومات الحساب:
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

    # ------------------------------------------------------------------
    # ADD ACTION (Dynamic Weight Adjustment)
    # ------------------------------------------------------------------
    def add_action(
        self,
        account_id: str,
        country: str,
        solution: str,
        action_type: str,
    ) -> Dict[str, Any]:
        """
        عند إضافة Action:
          - نحسب الوزن الجديد حسب الخوارزمية:
              * First touch  -> base_weight
              * Non-first    -> base_weight * (1 - last_touch_weight)
          - نعيد ترتيب Top4 باستخدام الوزن الجديد
        """

        # 1) تحديث وزن الحساب 
        adjusted_weight = update_account_weight(
            store=self.weight_store,
            account_id=account_id,
            action_type=action_type,
            base_weights=self.base_weights,
        )

        # 1.1) احصل على أوزان الـ Actions الخاصة بهذا الحساب (لكل نوع Action)
        state = self.weight_store.get(account_id)
        action_weights = dict(state.get("action_weights", {}) or {})

        # 2) جلب القوائم الأساسية
        by_country = self.store.top4_by_country(country)
        by_solution = self.store.top4_by_solution(solution)
        by_country_solution = self.store.top4_by_country_solution(country, solution)

        # 3) إعادة ترتيب مع وعي بالـ Action المضافة
        def rerank(df_top: pd.DataFrame) -> pd.DataFrame:
            if df_top is None or df_top.empty:
                return df_top

            df = df_top.copy()

            # وزن أساسي لكل مرشح
            df["base_weight"] = df["next_action"].map(
                lambda a: float(self.base_weights.get(a, 1.0))
            )

            # وزن خاص بالحساب لكل مرشح (يتغير بعد كل add_action)
            df["account_weight"] = df["next_action"].map(
                lambda a: float(action_weights.get(str(a), 1.0))
            )

            #  تكرار نفس الـ action مباشرة
            df["repeat_penalty"] = df["next_action"].apply(
                lambda a: 0.7 if a == action_type else 1.0
            )

            # score النهائي
            df["score"] = (
                df["count"].astype(float)
                * df["base_weight"]
                * df["account_weight"]
                * df["repeat_penalty"]
            )

            return (
                df.sort_values("score", ascending=False)
                  .head(4)
                  .reset_index(drop=True)
            )

        out_country = rerank(by_country)
        out_solution = rerank(by_solution)
        out_cs = rerank(by_country_solution)

        return {
            "account_id": str(account_id),
            "country": str(country),
            "solution": str(solution),
            "added_action": str(action_type),
            "adjusted_weight": float(adjusted_weight),
            "top4_by_country": (
                out_country.to_dict(orient="records") if out_country is not None else []
            ),
            "top4_by_solution": (
                out_solution.to_dict(orient="records") if out_solution is not None else []
            ),
            "top4_by_country_solution": (
                out_cs.to_dict(orient="records") if out_cs is not None else []
            ),
        }
