# Security Policy

## Purpose and Scope

The Explainable Decision Engine is a **demonstration and educational project** designed to model how modern financial institutions, payment processors, and fintech platforms architect secure, observable, and explainable risk decisioning systems.

This repository **does not represent a deployed production financial system**, but it intentionally mirrors **real-world security boundaries, controls, and operational concerns** found in internal banking tools.

The purpose of this security policy is to:

- Clearly define what security guarantees *do* and *do not* apply
- Establish responsible disclosure expectations
- Document authentication, authorization, and rate limiting design
- Address ML-specific security considerations
- Promote responsible use and ethical awareness

---

## Supported Versions

Security updates and fixes apply **only to the latest version on the `main` branch**.

| Version | Supported |
|-------|-----------|
| `main` | ✅ |
| Previous commits | ❌ |
| Forks | ❌ |

Users are encouraged to stay current with the latest commit to receive all security-related improvements.

---

## Responsible Disclosure

If you discover a security vulnerability, please follow **responsible disclosure practices**.

### What to Report

- Authentication bypasses
- Authorization or role escalation issues
- Rate limiting or abuse vulnerabilities
- Injection attacks (SQL, command, template, etc.)
- Data exposure or leakage
- Unsafe deserialization or model loading paths
- Denial-of-service vectors
- Any issue that could reasonably impact confidentiality, integrity, or availability

### How to Report

- **Do not open a public GitHub issue**
- Use GitHub’s private security advisory feature if available
- Alternatively, contact the repository owner directly

### Expectations

- Reports will be acknowledged in a reasonable timeframe
- This project makes **no guarantees of SLA or patch timelines**
- Findings may be fixed, documented as out-of-scope, or declined

---

## Data Privacy and Data Handling

### Synthetic Data Only

- All training, evaluation, and inference data used in this project is **synthetic**
- No real customer, merchant, bank, or transaction data is used
- No personal data is collected, stored, or transmitted

### API Requests

- Incoming requests are processed **in-memory**
- No request payloads are persisted by default
- Local UI history is stored only in the browser via `localStorage`

### Logs and Telemetry

- Logs may include request metadata (timestamps, endpoint, latency)
- Logs **do not include sensitive payload values by default**
- Telemetry is local-only unless explicitly configured otherwise

---

## Authentication and Authorization

### API Authentication

- All `/v1/*` endpoints (except `/v1/health`) require an `X-API-Key` header
- API keys are configured via environment variables
- Missing or invalid keys result in `401 Unauthorized` or `403 Forbidden`

### Role-Based Access

The system supports role differentiation (example):

- `admin`
- `analyst`
- `read_only`

Roles determine access to:
- Scoring and explain endpoints
- Model promotion
- Registry and monitoring views

### UI Authentication

- The web portal login is **demo-only**
- It simulates an internal authentication gate
- It stores a local authentication flag in browser storage
- **It is not a real identity system and should not be treated as one**

---

## Rate Limiting and Abuse Protection

The system includes **distributed rate limiting** using Redis:

- Limits are enforced per API key
- Different keys may have different quotas
- Limits apply across multiple instances

This design reflects how real internal APIs protect against:
- Abuse
- Accidental overload
- Noisy clients

Rate limiting is considered a **security and reliability control**, not just performance tuning.

---

## Observability and Auditability

The system emits:

- Structured JSON logs
- Request IDs
- Endpoint-level latency metrics
- Model version per request
- OpenTelemetry spans

This enables:
- Debugging
- Incident investigation
- Traceability
- Performance analysis

Observability is treated as a **first-class security feature**, not an afterthought.

---

## Model and ML-Specific Security Considerations

### Model Integrity

- Models are loaded from versioned artifact directories
- Promotion to `latest` is a controlled operation
- Registry metadata tracks training and promotion context

### Explainability Safety

- SHAP and fallback explainers are bounded and sanitized
- Outputs are numerical and descriptive only
- No executable code paths are derived from explanations

### Drift and Monitoring

- Feature drift is monitored via rolling statistics
- Alerts surface directly in API responses
- Drift detection is informational, not enforcement-based

### Calibration Awareness

- Probabilities are calibrated to a defined base rate
- Calibration metadata is exposed explicitly
- No claim is made that calibration reflects real-world institutions

---

## Limitations and Non-Goals

This project explicitly does **not**:

- Guarantee correctness for real financial decisions
- Replace bank-grade risk systems
- Certify fairness, compliance, or regulatory approval
- Store or protect real customer data
- Provide production-grade identity management

Any such usage would require **significant additional controls and governance**.

---

## Responsible Use

Users are expected to:

- Treat outputs as **demonstrative**
- Avoid deploying this system in real financial workflows
- Avoid representing outputs as real fraud or credit scores
- Respect the ethical implications of risk decisioning

This project exists to **teach engineering maturity**, not to operationalize financial risk.

---

## Security Philosophy

The Explainable Decision Engine follows these principles:

- **Defense in depth** over UI-only protection
- **Explicitness over magic**
- **Observability over blind trust**
- **Explainability over opaque scoring**
- **Responsible disclosure over secrecy**

Security is viewed as a **continuous engineering discipline**, not a checklist.

---

## License Context

This project is licensed under the MIT License.

The license permits reuse and modification but **does not imply warranty, fitness for purpose, or security guarantees**.

Users are responsible for any downstream use.


## Final Note

If you are reading this policy and the system is running end-to-end:

You are interacting with a **production-inspired ML system**, built to demonstrate how serious organizations think about **security, risk, and responsibility**.

That is intentional.
