from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import numpy as np
from sklearn.metrics import roc_auc_score, brier_score_loss


@dataclass
class EvalResult:
    auc: float
    brier: float

    def to_dict(self) -> Dict[str, Any]:
        return {"auc": self.auc, "brier": self.brier}


def evaluate_binary_probs(y_true: np.ndarray, y_prob: np.ndarray) -> EvalResult:
    auc = float(roc_auc_score(y_true, y_prob))
    brier = float(brier_score_loss(y_true, y_prob))
    return EvalResult(auc=auc, brier=brier)