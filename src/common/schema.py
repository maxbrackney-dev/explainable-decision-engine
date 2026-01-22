from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal, Optional, Dict, Any


class RiskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    age: int = Field(..., ge=13, le=100)
    income: float = Field(..., ge=0)
    account_age_days: int = Field(..., ge=0, le=36500)
    num_txn_30d: int = Field(..., ge=0, le=5000)
    avg_txn_amount_30d: float = Field(..., ge=0, le=100000)
    num_chargebacks_180d: int = Field(..., ge=0, le=200)
    device_change_count_30d: int = Field(..., ge=0, le=200)
    geo_distance_from_last_txn_km: float = Field(..., ge=0, le=20000)
    is_international: bool
    merchant_risk_score: float = Field(..., ge=0, le=1)


RiskLabel = Literal["high_risk", "low_risk"]
Decision = Literal["approve", "step_up", "review", "decline"]


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: str
    message: str


class RiskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_probability_event: float
    risk_label: RiskLabel
    decision: Decision
    expected_loss_usd: float
    model_version: str
    warnings: List[str]
    reason_codes: List[str]
    calibration_snapshot: Dict[str, Any]


class ExplainFeature(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature: str
    shap_value: float
    direction: Literal["increases_risk", "decreases_risk"]
    contribution_percent: float


class ExplainPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseline_probability: float
    predicted_probability: float
    top_features: List[ExplainFeature]


class ExplainResponse(RiskResponse):
    explanation: ExplainPayload


class ModelInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    training_date: str
    model_type: str
    model_version: str
    metrics: dict
    feature_list: List[str]
    thresholds: dict
    limitations: str
    fairness_report: Optional[dict] = None


class GlobalExplainItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature: str
    mean_abs_shap: float
    importance_percent: float


class GlobalExplainResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_version: str
    items: List[GlobalExplainItem]
    plot_path: Optional[str] = None


class DriftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_key: str
    threshold: float
    features: List[dict]
