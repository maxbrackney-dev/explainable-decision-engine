from __future__ import annotations

import joblib
from fastapi import APIRouter, Depends, Request, HTTPException

from src.common.schema import (
    RiskRequest, RiskResponse, ExplainResponse,
    ExplainPayload, ExplainFeature,
    ModelInfo, GlobalExplainResponse, GlobalExplainItem, DriftResponse
)
from src.common.settings import SETTINGS
from src.common.logging import get_logger, LogTimer, with_ctx
from src.common.auth import require_principal, require_admin, require_write, Principal
from src.common.rate_limit import check_rate_limit
from src.common.decisioning import expected_loss_usd, decision_from_prob, merge_reason_codes, calibration_snapshot
from src.common.drift import update_drift_stats, drift_warnings, drift_summary
from src.common.model_registry import promote, load_registry
from src.common.utils import normalize_features_ordered

from src.serving.model_loader import load_artifacts
from src.serving.scorer import predict_probability, ood_warnings
from src.serving.explainer import build_explainer, explain_local, explain_global

router = APIRouter()
logger = get_logger("api")

ART = load_artifacts()

_bg_df = joblib.load(ART.artifacts_dir / SETTINGS.shap_background_filename)
EXPLAINER = build_explainer(ART.model, _bg_df, ART.feature_list)


@router.get("/health")
def health(request: Request) -> dict:
    rid = getattr(request.state, "request_id", "unknown")
    return {"status": "ok", "model_version": ART.metrics.get("training_date", "unknown"), "request_id": rid}


def _auth(principal: Principal = Depends(require_principal)) -> Principal:
    check_rate_limit(principal)
    return principal


@router.get("/auth/me")
def auth_me(request: Request, principal: Principal = Depends(_auth)) -> dict:
    return {
        "status": "ok",
        "principal": principal.to_dict(),
        "event_definition": SETTINGS.event_definition,
    }


@router.post("/score", response_model=RiskResponse)
def score(req: RiskRequest, request: Request, principal: Principal = Depends(_auth)) -> RiskResponse:
    require_write(principal)

    request_id = getattr(request.state, "request_id", "unknown")
    t = LogTimer()
    log = with_ctx(logger, {"request_id": request_id, "endpoint": "score", "model_version": ART.metrics.get("training_date")})

    payload = req.model_dump()

    prob = predict_probability(ART.model, payload, ART.feature_list)
    label = "high_risk" if prob >= float(ART.metrics.get("thresholds", {}).get("review", SETTINGS.review_threshold)) else "low_risk"
    decision = decision_from_prob(prob)
    exp_loss = expected_loss_usd(prob, payload)

    warnings = []
    warnings += ood_warnings(payload, ART.stats_means, ART.stats_stds, SETTINGS.drift_z_threshold)
    update_drift_stats(principal.api_key, payload, ART.feature_list)
    warnings += drift_warnings(principal.api_key, ART.stats_means, ART.stats_stds, ART.feature_list)

    reasons = merge_reason_codes(None, payload)

    resp = RiskResponse(
        risk_probability_event=float(prob),
        risk_label=label,  # type: ignore
        decision=decision,  # type: ignore
        expected_loss_usd=float(exp_loss),
        model_version=str(ART.metrics.get("training_date", "unknown")),
        warnings=warnings,
        reason_codes=reasons,
        calibration_snapshot=calibration_snapshot(ART.metrics),
    )

    log.info("scored", extra={"ctx": {"request_id": request_id, "latency_ms": t.ms(), "risk_probability_event": float(prob), "decision": decision}})
    return resp


@router.post("/explain", response_model=ExplainResponse)
def explain(req: RiskRequest, request: Request, principal: Principal = Depends(_auth)) -> ExplainResponse:
    require_write(principal)

    request_id = getattr(request.state, "request_id", "unknown")
    t = LogTimer()
    log = with_ctx(logger, {"request_id": request_id, "endpoint": "explain", "model_version": ART.metrics.get("training_date")})

    payload = req.model_dump()

    prob = predict_probability(ART.model, payload, ART.feature_list)
    label = "high_risk" if prob >= float(ART.metrics.get("thresholds", {}).get("review", SETTINGS.review_threshold)) else "low_risk"
    decision = decision_from_prob(prob)
    exp_loss = expected_loss_usd(prob, payload)

    warnings = []
    warnings += ood_warnings(payload, ART.stats_means, ART.stats_stds, SETTINGS.drift_z_threshold)
    update_drift_stats(principal.api_key, payload, ART.feature_list)
    warnings += drift_warnings(principal.api_key, ART.stats_means, ART.stats_stds, ART.feature_list)

    x_row_df = normalize_features_ordered(payload, ART.feature_list)
    local = explain_local(EXPLAINER, ART.model, x_row_df, ART.feature_list, top_k=6)

    top_features = [
        ExplainFeature(
            feature=item["feature"],
            shap_value=float(item["shap_value"]),
            direction=item["direction"],
            contribution_percent=float(item["contribution_percent"]),
        )
        for item in local.top_features
    ]

    reasons = merge_reason_codes([tf.model_dump() for tf in top_features], payload)

    resp = ExplainResponse(
        risk_probability_event=float(prob),
        risk_label=label,  # type: ignore
        decision=decision,  # type: ignore
        expected_loss_usd=float(exp_loss),
        model_version=str(ART.metrics.get("training_date", "unknown")),
        warnings=warnings,
        reason_codes=reasons,
        calibration_snapshot=calibration_snapshot(ART.metrics),
        explanation=ExplainPayload(
            baseline_probability=float(local.baseline_probability),
            predicted_probability=float(local.predicted_probability),
            top_features=top_features,
        ),
    )

    log.info("explained", extra={"ctx": {"request_id": request_id, "latency_ms": t.ms(), "risk_probability_event": float(prob), "decision": decision}})
    return resp


@router.get("/global-explain", response_model=GlobalExplainResponse)
def global_explain(request: Request, principal: Principal = Depends(_auth), save_plot: bool = True) -> GlobalExplainResponse:
    """
    Production-style:
    - cache global explain result to artifacts/latest/global_explain_cached.json
    - use safe Kernel SHAP with small nsamples/max_rows
    - fallback to permutation importance if SHAP fails
    """
    cache_path = ART.artifacts_dir / "global_explain_cached.json"
    if cache_path.exists():
        try:
            import json
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            items = cached.get("items", [])
            resp_items = [
                GlobalExplainItem(
                    feature=i["feature"],
                    mean_abs_shap=float(i["mean_abs_shap"]),
                    importance_percent=float(i["importance_percent"]),
                )
                for i in items
            ]
            return GlobalExplainResponse(
                model_version=str(ART.metrics.get("training_date", "unknown")),
                items=resp_items,
                plot_path=cached.get("plot_path"),
            )
        except Exception:
            # ignore cache parse errors
            pass

    sample_df = joblib.load(ART.artifacts_dir / SETTINGS.global_shap_sample_filename)

    # robust explainer call (never throws due to fallback)
    items, method = explain_global(EXPLAINER, ART.model, sample_df, ART.feature_list, max_rows=80)

    plot_path = None
    if save_plot:
        try:
            import matplotlib.pyplot as plt
            top = items[:10]
            labels = [d["feature"] for d in top]
            values = [d["mean_abs_shap"] for d in top]
            plt.figure(figsize=(8, 4))
            plt.barh(list(reversed(labels)), list(reversed(values)))
            plt.title(f"Global Feature Importance ({method})")
            plt.xlabel("importance")
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

    # cache for next time
    try:
        import json
        cache_path.write_text(
            json.dumps({"items": items, "plot_path": plot_path, "method": method}, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass

    return GlobalExplainResponse(
        model_version=str(ART.metrics.get("training_date", "unknown")),
        items=resp_items,
        plot_path=plot_path,
    )


@router.get("/model-info", response_model=ModelInfo)
def model_info(request: Request, principal: Principal = Depends(_auth)) -> ModelInfo:
    limitations = (ART.metrics.get("limitations", "") + "\n\n" + ART.model_card.strip())[:8000]
    return ModelInfo(
        training_date=str(ART.metrics.get("training_date", "unknown")),
        model_type=str(ART.metrics.get("model_type", "unknown")),
        model_version=str(ART.metrics.get("training_date", "unknown")),
        metrics=ART.metrics,
        feature_list=ART.feature_list,
        thresholds=ART.metrics.get("thresholds", {}),
        limitations=limitations,
        fairness_report=ART.fairness_report or None,
    )


@router.get("/monitor/drift", response_model=DriftResponse)
def monitor_drift(request: Request, principal: Principal = Depends(_auth)) -> DriftResponse:
    s = drift_summary(principal.api_key, ART.stats_means, ART.stats_stds, ART.feature_list)
    return DriftResponse(api_key=principal.api_key, threshold=float(s.get("threshold", SETTINGS.drift_z_threshold)), features=s.get("features", []))


@router.get("/admin/registry")
def admin_registry(request: Request, principal: Principal = Depends(_auth)) -> dict:
    require_admin(principal)
    return load_registry()


@router.post("/admin/promote")
def admin_promote(version: str, promoted_by: str = "demo", request: Request = None, principal: Principal = Depends(_auth)) -> dict:
    require_admin(principal)
    require_write(principal)

    try:
        promote(version=version, promoted_by=promoted_by)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": str(e)})
    return {"status": "ok", "latest": version, "promoted_by": promoted_by}
