# Explainable Decision Engine
**Production-style Risk Scoring, Explainability, and Decisioning Platform (with Analyst Portal UI)**

---

## Executive Summary

The Explainable Decision Engine is a production-inspired risk scoring system designed to mirror how modern banks, payment processors, and fintech platforms evaluate fraud, chargeback, or default risk in real time.

This project is intentionally not a toy ML demo. It models the full lifecycle of a real risk system:

- Model training and versioning
- Calibrated probability outputs tied to a defined event horizon
- Cost-aware decision thresholds (approve / step-up / review / decline)
- Per-request explainability (SHAP)
- Global feature importance (cached + robust fallback)
- Drift detection and monitoring hooks
- Authentication, rate limiting, and observability
- Analyst-friendly UI and API documentation

Although the underlying data is synthetic, the architecture, outputs, and interfaces are directly comparable to internal systems used at banks and large fintechs.

---

## What This System Predicts (Explicit Contract)

This model outputs:

P(chargeback within 180 days of transaction)

All probabilities are:
- Event-specific
- Time-bounded
- Calibrated to a base rate
- Interpretable via feature attribution

This is not a generic “risk score.” It is a probability of a concrete business event within a defined horizon.

---

## Core Outputs

Each scoring request returns:

- risk_probability_event  
  Probability of the defined event occurring within the horizon

- expected_loss_usd  
  risk_probability × loss_given_event

- decision  
  One of: approve, step_up, review, decline

- reason_codes  
  SHAP-based explanations with rule-based fallbacks

- warnings  
  Drift, out-of-distribution, or calibration alerts

- calibration_snapshot  
  Base rate, calibration window, and model metadata

This mirrors how real bank decision engines communicate downstream.

---

## System Architecture

Client
→ FastAPI Application
→ Scoring Engine + Explainability Engine (SHAP)
→ Model Registry + Artifacts
→ Monitoring, Drift Detection, and Observability

FastAPI Layer Includes:
- Auth (X-API-Key)
- Rate limiting (Redis-backed)
- Validation (Pydantic)
- Tracing (OpenTelemetry)
- Structured logging (JSON)

Artifacts:
- artifacts/<version>/
- artifacts/registry.json
- artifacts/latest (promoted model)

---

## Authentication Model

All /v1/* endpoints (except /v1/health) require:

X-API-Key: <your-api-key>

- Keys are stored via environment variables
- Missing or invalid keys return HTTP 401/403
- Admin endpoints require elevated roles
- Keys may be read-only or role-scoped depending on configuration

This enforces real security boundaries, not UI-only protection.

---

## Observability and Monitoring

The system emits:
- Structured JSON logs
- request_id per request
- Endpoint latency
- Model version per response
- OpenTelemetry spans for all endpoints

This enables production-style debugging and performance analysis.

---

## Local Setup (Canonical Path)

1) Clone the repository

```bash
git clone https://github.com/maxbrackney-dev/explainable-decision-engine.git
cd explainable-decision-engine
```
2. Create and activate virtual environment
```bash
   python -m venv .venv
source .venv/bin/activate
```
3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
4. Set environment variables
   ```bash
   export DEMO_API_KEY=dev-demo-key
   export ENVIRONMENT=dev
   ```
5. Train the model
   ```bash
   python -m src.training.train
   ```
Verify artifacts:
```bash
ls artifacts/latest
```
Expected files:

- model.joblib
- metrics.json
- feature_schema.json
- model_card.md
- shap_background.joblib
- global_shap_sample.joblib
- fairness_report.json

6. Start the API server
   ```bash
   uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
   ```
## How to Open the UI in Codespaces (IMPORTANT)

If you are running this in GitHub Codespaces, you do not open http://127.0.0.1:8000
 in your browser.

Codespaces runs inside a container, so you must use the forwarded port URL.

1. Start the API (leave it running)
   ```bash
   python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
   ```
2. In Codespaces, open the Ports tab:
   - Look at the bottom panel in VS Code
   - Click “Ports”
   - Find port 8000

3. Click “Open in Browser” for port 8000
   This opens a URL like:
   https://<your-codespace-name>-8000.app.github.dev/

That is the correct browser URL.

4. Use these pages:
   - Landing page: https://<your-codespace-name>-8000.app.github.dev/
   - Login: https://<your-codespace-name>-8000.app.github.dev/login
   - Portal UI: https://<your-codespace-name>-8000.app.github.dev/app
   - Metrics: https://<your-codespace-name>-8000.app.github.dev/metrics
   - Audit: https://<your-codespace-name>-8000.app.github.dev/audit
   - Swagger: https://<your-codespace-name>-8000.app.github.dev/docs

# Analyst Portal UI (Complete Guide)
This project includes a full analyst-facing portal designed to look and behave like an internal fintech tool.

The portal includes:
   - Demo login
   - Theme toggle (dark/light)
   - Environment selector (dev/stage/prod)
   - API key storage + validation
   - Risk scoring + explainability controls
   - Global importance chart
   - Request history timeline
   - Audit table + CSV export
   - Metrics dashboard pulling model info + global explain
   - PDF report export (Print → Save as PDF)
   - Role-based UI behavior (read-only keys disable actions)

## 1) Landing Page (/)

**Route:**

`/`

**Purpose:**

Overview and navigation entrypoint

Links into Portal, Swagger, and health

**What to do:**

- Click “Open Portal” to go to login
- Use “API Docs” to open Swagger
- Use “Health” to verify the backend is running

---

## 2) Login Page (/login)

**Route:**

`/login`

**Purpose:**

Demo-only authentication gate to simulate a protected internal tool

**How it works:**

- This login is not real auth.
- It stores a local “authenticated” flag in `localStorage`.
- If you are not logged in, portal pages redirect back to `/login`.

**How to use:**

- Enter any email and any password (non-empty)
- Click “Sign in”
- You will be redirected to `/app`

**Logout behavior:**

- Clicking Logout clears the local auth flag and returns you to `/login`.

---

## 3) Theme Toggle (Dark / Light)

**Where:**

Top-right “Theme” button on most pages

**What it does:**

- Switches between a dark and light theme
- Saves your preference in `localStorage` so it persists between refreshes

**How to use:**

- Click Theme
- The UI immediately re-styles without a reload
- Refresh the page and it stays in your chosen mode

---

## 4) Portal Page (/app)

**Route:**

`/app`

This is the main interface: score, explain, monitor, and export.

---

### 4.1 Left Sidebar Controls

**Environment Selector**

- Dropdown: Dev / Stage / Prod
- UI-only by default
- Intended to simulate switching between different backend base URLs
- In this demo, all environments point to the same API unless you wire stage/prod separately

**API Key (demo)**

- Password input
- Stored in `localStorage`
- Used automatically on every API request as the `X-API-Key` header

**What to enter:**

If you set `DEMO_API_KEY=dev-demo-key`, enter:

`dev-demo-key`

If you configured `DEMO_API_KEYS_JSON`, enter one of the keys from that mapping.

**If API key is missing:**

- Protected endpoints return 401
- You will see errors in the Raw Response panel

**Load Sample Buttons**

- Low Risk: fills the form with a low-risk synthetic profile
- High Risk: fills the form with a high-risk synthetic profile

Use these to quickly generate meaningful differences in model output and explanations.

**Request History**

- Stores recent requests in `localStorage`
- Shows:
  - label (low_risk / high_risk)
  - probability
  - warning count
  - timestamp
- Click an entry to restore input and results

**Clear**

- Clears local history storage

**Audit Table**

- Opens `/audit` where requests can be browsed in tabular form and exported to CSV

---

### 4.2 Main Risk Input Form

**Fields:**

- age
- income
- account_age_days
- num_txn_30d
- avg_txn_amount_30d
- num_chargebacks_180d
- device_change_count_30d
- geo_distance_from_last_txn_km
- is_international
- merchant_risk_score

**Important:**

- The backend enforces strict validation ranges.
- Invalid values return 422 with a detailed schema error.

---

### 4.3 Action Buttons

**Score**

- Calls `POST /v1/score`
- Returns:
  - risk_probability_event
  - expected_loss_usd
  - decision
  - warnings
  - reason_codes

**Score + Explain**

- Calls `POST /v1/explain`
- Includes everything from `/score` plus:
  - explanation.top_features

**Global Explain**

- Calls `GET /v1/global-explain`
- Populates the “Global Feature Importance” chart
- Cached and resilient:
  - First run computes and caches
  - Later runs return immediately
- If SHAP fails, fallback permutation importance is used

**PDF Report**

- Opens `/report` in a new tab
- The report is generated client-side from the last explain response
- Click “Download PDF” to print-to-PDF

---

### 4.4 Results Panel

**Risk Probability**

- Shows `risk_probability_event`

**Risk Label**

- `low_risk` or `high_risk`

**Model Version**

- Typically training_date or a version identifier

**Warnings**

- OOD warnings (z-score based)
- Drift warnings (rolling distribution vs training stats)

**Top Features**

- SHAP top contributors
- Each shows:
  - feature name
  - direction (increases_risk / decreases_risk)
  - contribution percent
  - shap value

**Global Feature Importance Chart**

- Populated from `/v1/global-explain`

If it says “No data yet”:

- The global explain call did not succeed
- Check Raw Response for a 401 / 403 / 500
- Ensure API key is set

**Raw Response**

- Always shows the last response payload or error
- This is your “truth panel” for debugging the UI

---

### 4.5 Read-Only Mode Behavior

- If your API key is configured as read-only:
  - Score and Explain actions are disabled
  - PDF report is disabled
  - You can still view metrics, registry, and global explain (depending on role)

The portal determines this by calling:

`GET /v1/auth/me`

If `read_only` is true:

- Buttons are disabled
- Raw response displays role and access mode

---

## 5) Audit Page (/audit)

**Route:**

`/audit`

**Purpose:**

Bank-like audit trail view

Browse, filter, and export interactions

**Features:**

- Filter search box
- Label filter (high_risk / low_risk)
- Table listing:
  - timestamp
  - env
  - label
  - probability
  - warning count
- Export CSV button
- Clear audit history button
- “Load” action restores a record back in the portal (via localStorage)

---

## 6) Metrics Dashboard (/metrics)

**Route:**

`/metrics`

**Purpose:**

Model performance and explainability monitoring view

This page calls protected endpoints:

- `GET /v1/model-info`
- `GET /v1/global-explain`

If your API key is missing or invalid, you will see 401 errors.

**Features:**

- Connection panel:
  - environment selector
  - api key input
  - save key
  - connection status
- Model summary cards:
  - model type
  - version
  - AUC
  - Brier score
- Global importance chart
- Raw model info JSON block for full visibility

---

## 7) Report Page (/report)

**Route:**

`/report`

**Purpose:**

Printable decision packet (client-side)

Resembles what an analyst might export into a case management system

**How it works:**

- The portal stores last explain result in `localStorage`
- Report page reads it and renders:
  - decision summary
  - warnings
  - input snapshot
  - top SHAP features
  - raw response

**Download PDF**

- Click “Download PDF”
- Browser opens print dialog
- Choose “Save as PDF”

## How to Use the System (API)

### 1) Health Check

curl http://127.0.0.1:8000/v1/health


### 2) Score

curl -X POST http://127.0.0.1:8000/v1/score \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-demo-key" \
  -d '{
    "age": 34,
    "income": 85000,
    "account_age_days": 540,
    "num_txn_30d": 22,
    "avg_txn_amount_30d": 120.5,
    "num_chargebacks_180d": 0,
    "device_change_count_30d": 1,
    "geo_distance_from_last_txn_km": 3.2,
    "is_international": false,
    "merchant_risk_score": 0.18
  }'


### 3) Explain

curl -X POST http://127.0.0.1:8000/v1/explain \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-demo-key" \
  -d '{
    "age": 19,
    "income": 12000,
    "account_age_days": 12,
    "num_txn_30d": 48,
    "avg_txn_amount_30d": 310.9,
    "num_chargebacks_180d": 2,
    "device_change_count_30d": 5,
    "geo_distance_from_last_txn_km": 1400,
    "is_international": true,
    "merchant_risk_score": 0.92
  }'


### 4) Global Explain

curl -H "X-API-Key: dev-demo-key" \
  http://127.0.0.1:8000/v1/global-explain


### 5) Auth Identity

curl -H "X-API-Key: dev-demo-key" \
  http://127.0.0.1:8000/v1/auth/me


## Model Registry and Versioning

Each model lives in:

artifacts/<version>/

registry.json tracks:
- training date
- metrics
- calibration info
- promotion metadata

Admin promotion:
- promotes a version to artifacts/latest
- requires admin role


## Drift Detection

The system tracks:
- Feature distribution shifts
- Rolling inference statistics
- Training vs live deltas

Warnings surface directly in API responses.

Monitoring endpoint:

GET /v1/monitor/drift


## Fairness and Limitations

Each training run generates:
- Metrics by age bucket
- Explicit disclaimers
- Non-certification language

This demonstrates responsible ML practice even on synthetic data.


## Important Disclaimers

- Data is synthetic
- Probabilities are calibrated to synthetic labels
- Outputs are not transferable without retraining
- This is a demonstration of engineering maturity, not a deployed financial product


## Why This Project Exists

This repository demonstrates:
- End-to-end ML system ownership
- Production-grade thinking
- Risk decisioning realism
- Explainability done correctly
- Observability and security awareness

This is the kind of system built internally, not shown publicly.


## License

MIT (educational and demonstration use)
