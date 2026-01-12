from __future__ import annotations

from typing import Any, Dict, List

import joblib
from fastapi import APIRouter, Request, HTTPException

from src.common.schema import (
    RiskRequest,
    RiskResponse,
    ExplainResponse,
    ExplainPayload,
    ExplainFeature,
    ModelInfo,
    GlobalExplainResponse,
    GlobalExplainItem,
    BatchScoreRequest,
    BatchScoreResponse,
)
from src.common.settings import SETTINGS
from src.common.logging import get_logger, LogTimer, with_ctx
from src.common.utils import normalize_features_ordered
from src.common.metrics_queue import emit_metric
from src.serving.model_loader import load_artifacts
from src.serving.scorer import predict_probability, compute_warnings, label_from_threshold
from src.serving.explainer import build_explainer, explain_local, explain_global

router = APIRouter()
logger = get_logger("api")

ART = load_artifacts()

# Load SHAP background as DataFrame (training saved it as a DataFrame)
_bg_df = joblib.load(ART.artifacts_dir / SETTINGS.shap_background_filename)

# IMPORTANT: build_explainer now expects (model, background_df, feature_list)
EXPLAINER = build_explainer(ART.model, _bg_df, ART.feature_list)

CPP_CORE_AVAILABLE = False
cpp_core = None
try:
    import decision_engine_core as cpp_core  # type: ignore
    CPP_CORE_AVAILABLE = True
except Exception:
    CPP_CORE_AVAILABLE = False


def _engine_guardrails(
    prob: float,
    threshold: float,
    payload_dict: Dict[str, Any],
    means: Dict[str, float],
    stds: Dict[str, float],
):
    if CPP_CORE_AVAILABLE and cpp_core is not None:
        warnings = cpp_core.ood_warnings(payload_dict, means, stds, float(SETTINGS.ood_z_threshold))
        label = cpp_core.label_from_threshold(float(prob), float(threshold))
        return label, warnings, True

    warnings = compute_warnings(payload_dict, means, stds)
    label = label_from_threshold(float(prob), float(threshold))
    return label, warnings, False


@router.get("/health")
def health(request: Request) -> dict:
    rid = getattr(request.state, "request_id", "unknown")
    return {"status": "ok", "model_version": SETTINGS.model_version, "request_id": rid}


@router.post("/score", response_model=RiskResponse)
def score(req: RiskRequest, request: Request) -> RiskResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    t = LogTimer()
    log = with_ctx(logger, {"request_id": request_id, "endpoint": "score"})

    payload = req.model_dump()
    prob = predict_probability(ART.model, payload, ART.feature_list)
    threshold = float(ART.metrics.get("threshold", 0.5))

    label, warnings, used_cpp = _engine_guardrails(prob, threshold, payload, ART.stats_means, ART.stats_stds)

    latency_ms = t.ms()
    log.info(
        "scored",
        extra={"ctx": {"request_id": request_id, "latency_ms": latency_ms, "risk_probability": round(prob, 6), "risk_label": label, "used_cpp_core": used_cpp}},
    )

    emit_metric({"event": "score", "request_id": request_id, "latency_ms": latency_ms, "risk_probability": float(prob), "risk_label": label, "model_version": SETTINGS.model_version})

    return RiskResponse(
        risk_probability=float(prob),
        risk_label=label,  # type: ignore
        model_version=SETTINGS.model_version,
        warnings=warnings,
    )


@router.post("/batch-score", response_model=BatchScoreResponse)
def batch_score(req: BatchScoreRequest, request: Request) -> BatchScoreResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    t = LogTimer()
    log = with_ctx(logger, {"request_id": request_id, "endpoint": "batch-score"})

    items = req.items
    if len(items) > SETTINGS.batch_max_rows:
        raise HTTPException(status_code=413, detail=f"batch_too_large: max={SETTINGS.batch_max_rows}")

    threshold = float(ART.metrics.get("threshold", 0.5))
    results: List[RiskResponse] = []

    for it in items:
        payload = it.model_dump()
        prob = predict_probability(ART.model, payload, ART.feature_list)
        label, warnings, _ = _engine_guardrails(prob, threshold, payload, ART.stats_means, ART.stats_stds)
        results.append(
            RiskResponse(
                risk_probability=float(prob),
                risk_label=label,  # type: ignore
                model_version=SETTINGS.model_version,
                warnings=warnings,
            )
        )

    latency_ms = t.ms()
    log.info("batch_scored", extra={"ctx": {"request_id": request_id, "latency_ms": latency_ms, "count": len(results)}})

    emit_metric({"event": "batch_score", "request_id": request_id, "latency_ms": latency_ms, "count": len(results), "model_version": SETTINGS.model_version})

    return BatchScoreResponse(model_version=SETTINGS.model_version, count=len(results), results=results)


@router.post("/explain", response_model=ExplainResponse)
def explain(req: RiskRequest, request: Request) -> ExplainResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    t = LogTimer()
    log = with_ctx(logger, {"request_id": request_id, "endpoint": "explain"})

    payload = req.model_dump()
    prob = predict_probability(ART.model, payload, ART.feature_list)
    threshold = float(ART.metrics.get("threshold", 0.5))

    label, warnings, used_cpp = _engine_guardrails(prob, threshold, payload, ART.stats_means, ART.stats_stds)

    x_row_df = normalize_features_ordered(payload, ART.feature_list)

    local = explain_local(EXPLAINER, ART.model, x_row_df, ART.feature_list, top_k=SETTINGS.explain_top_k)

    top_features = [
        ExplainFeature(
            feature=item["feature"],
            shap_value=float(item["shap_value"]),
            direction=item["direction"],
            contribution_percent=float(item["contribution_percent"]),
        )
        for item in local.top_features
    ]

    latency_ms = t.ms()
    log.info(
        "explained",
        extra={"ctx": {"request_id": request_id, "latency_ms": latency_ms, "risk_probability": round(prob, 6), "risk_label": label, "used_cpp_core": used_cpp}},
    )

    emit_metric({"event": "explain", "request_id": request_id, "latency_ms": latency_ms, "risk_probability": float(prob), "risk_label": label, "model_version": SETTINGS.model_version})

    return ExplainResponse(
        risk_probability=float(prob),
        risk_label=label,  # type: ignore
        model_version=SETTINGS.model_version,
        warnings=warnings,
        explanation=ExplainPayload(
            baseline_probability=float(local.baseline_probability),
            predicted_probability=float(local.predicted_probability),
            top_features=top_features,
        ),
    )


@router.get("/model-info", response_model=ModelInfo)
def model_info() -> ModelInfo:
    limitations = ART.metrics.get("limitations", "") + "\n\n" + ART.model_card.strip()
    return ModelInfo(
        training_date=str(ART.metrics.get("training_date", "unknown")),
        model_type=str(ART.metrics.get("model_type", "unknown")),
        model_version=SETTINGS.model_version,
        metrics=ART.metrics,
        feature_list=ART.feature_list,
        threshold=float(ART.metrics.get("threshold", 0.5)),
        limitations=limitations[:6000],
    )


@router.get("/global-explain", response_model=GlobalExplainResponse)
def global_explain(save_plot: bool = True) -> GlobalExplainResponse:
    sample_df = joblib.load(ART.artifacts_dir / SETTINGS.global_shap_sample_filename)
    items = explain_global(EXPLAINER, sample_df, ART.feature_list, max_rows=500)

    plot_path = None
    if save_plot:
        try:
            import matplotlib.pyplot as plt

            top = items[:10]
            labels = [d["feature"] for d in top]
            values = [d["mean_abs_shap"] for d in top]

            plt.figure(figsize=(8, 4))
            plt.barh(list(reversed(labels)), list(reversed(values)))
            plt.title("Global SHAP Feature Importance (mean |SHAP|)")
            plt.xlabel("mean |SHAP|")
            plt.tight_layout()

            out = ART.artifacts_dir / "global_shap_importance.png"
            plt.savefig(out)
            plt.close()
            plot_path = str(out)
        except Exception:
            plot_path = None

    resp_items = [
        GlobalExplainItem(
            feature=d["feature"],
            mean_abs_shap=float(d["mean_abs_shap"]),
            importance_percent=float(d["importance_percent"]),
        )
        for d in items
    ]

    return GlobalExplainResponse(model_version=SETTINGS.model_version, items=resp_items, plot_path=plot_path)
