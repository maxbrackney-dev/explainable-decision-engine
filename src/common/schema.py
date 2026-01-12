from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal, Optional


class RiskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    age: int = Field(..., ge=13, le=100, examples=[34])
    income: float = Field(..., ge=0, examples=[78000])
    account_age_days: int = Field(..., ge=0, le=36500, examples=[400])
    num_txn_30d: int = Field(..., ge=0, le=5000, examples=[22])
    avg_txn_amount_30d: float = Field(..., ge=0, le=100000, examples=[55.25])
    num_chargebacks_180d: int = Field(..., ge=0, le=200, examples=[0])
    device_change_count_30d: int = Field(..., ge=0, le=200, examples=[1])
    geo_distance_from_last_txn_km: float = Field(..., ge=0, le=20000, examples=[10.0])
    is_international: bool = Field(..., examples=[False])
    merchant_risk_score: float = Field(..., ge=0, le=1, examples=[0.15])


RiskLabel = Literal["high_risk", "low_risk"]


class RiskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_probability: float
    risk_label: RiskLabel
    model_version: str
    warnings: List[str]


class BatchScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: List[RiskRequest] = Field(..., min_length=1)


class BatchScoreResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_version: str
    count: int
    results: List[RiskResponse]


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
    threshold: float
    limitations: str


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