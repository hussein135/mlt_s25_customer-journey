# src/weights.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional
import json


# أوزان أساسية (  1.0 للجميع، )
DEFAULT_BASE_WEIGHTS: Dict[str, float] = {
    "Email": 1.0,
    "Call": 1.0,
    "Meeting": 1.0,
    "Follow Up": 1.0,
    "Review": 1.0,
    "Demo": 1.0,
    "1St Appointment": 1.0,
    "2Nd Appointment": 1.0,
}

# Floors لمنع الانهيار للصفر
MIN_LAST_TOUCH_WEIGHT = 0.05   # يمنع last_touch_weight من أن يصبح 0
MIN_ADJUSTED_WEIGHT = 0.05     # يمنع adjusted_weight من أن يصبح 0


@dataclass
class AccountWeightStore:
    """
    تخزين حالة كل حساب (MVP) في JSON:
      - last_touch_weight
      - last_action
      - is_first_touch
      - touch_count
      - action_weights (وزن لكل نوع Action داخل الحساب)
    """
    state_path: Path

    def __post_init__(self) -> None:
        self.state_path = Path(self.state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_path.exists():
            self._write({})

    def _read(self) -> Dict[str, Any]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write(self, data: Dict[str, Any]) -> None:
        self.state_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def get(self, account_id: str) -> Dict[str, Any]:
        data = self._read()
        return data.get(
            str(account_id),
            {
                "last_touch_weight": 0.0,
                "last_action": None,
                "is_first_touch": True,
                "touch_count": 0,
                "action_weights": {},
            }
        )

    def set(self, account_id: str, state: Dict[str, Any]) -> None:
        data = self._read()
        data[str(account_id)] = state
        self._write(data)


def adjust_weight_first_touch(base_weight: float) -> float:
    # Apply Initial Weight
    return float(base_weight)


def adjust_weight_non_first_touch(base_weight: float, last_touch_weight: float) -> float:
    # NewWeight = BaseWeight * (1 - LastTouchWeight)
    raw = float(base_weight) * (1.0 - float(last_touch_weight))
    return max(raw, MIN_ADJUSTED_WEIGHT)


def update_account_weight(
    store: AccountWeightStore,
    account_id: str,
    action_type: str,
    base_weights: Optional[Dict[str, float]] = None
) -> float:
    """
    عند إضافة Action:
      - إذا أول touch: adjusted = base_weight(action_type)
      - غير ذلك: adjusted = base_weight(action_type) * (1 - last_touch_weight_prev)
    ثم نخزن last_touch_weight = adjusted
    """
    if base_weights is None:
        base_weights = DEFAULT_BASE_WEIGHTS

    state = store.get(account_id)
    last_touch_weight_prev = float(state.get("last_touch_weight", 0.0))
    # دعم ترحيل الحالة القديمة: touch_count/action_weights قد لا تكون موجودة
    touch_count = int(state.get("touch_count", 0))
    action_weights = dict(state.get("action_weights", {}) or {})
    is_first_touch = bool(state.get("is_first_touch", touch_count == 0))


    base = float(base_weights.get(action_type, 1.0))

    if is_first_touch:
        adjusted = adjust_weight_first_touch(base)
        is_first_touch = False
    else:
        adjusted = adjust_weight_non_first_touch(base, last_touch_weight_prev)

    # Floor للوزن المحسوب
    adjusted = max(adjusted, MIN_ADJUSTED_WEIGHT)

    # خزّن الحالة (مع floor لآخر لمسّة أيضاً)
    action_weights[str(action_type)] = float(adjusted)
    touch_count = touch_count + 1

    # خزّن الحالة (مع floor لآخر لمسّة أيضاً)
    store.set(account_id, {
        "last_touch_weight": max(adjusted, MIN_LAST_TOUCH_WEIGHT),
        "last_action": action_type,
        "is_first_touch": is_first_touch,
        "touch_count": touch_count,
        "action_weights": action_weights,
    })
    return adjusted
