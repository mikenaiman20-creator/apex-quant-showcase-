# Apex Quant v2

An institutional-grade, containerized algorithmic trading and quantitative research platform engineered around **fail-closed safety architecture**, **cryptographic execution boundaries**, and **zero-placeholder QA verification**.

> **Project Status:** Active Development — Paper Trading & Research Sandbox (`LIVE_TRADING=False`). Currently enforcing a 22-point Functional Requirements Document (FRD) certification suite (18/22 passing).

---

## Core Engineering Philosophy

Most retail algorithmic trading repositories optimize for backtest aesthetics while ignoring operational failure modes. Apex Quant v2 is built from the inside out around three non-negotiable rules:

1. **Fail-Closed By Default:** If the Risk Engine is unreachable, returns an anomalous state, or fails cryptographic signature validation, the execution bot immediately halts and enters `STANDBY` rather than degrading to unguarded execution.
2. **Zero Certification Theater:** Every verification check in `Apex_Quant_QA.py` evaluates real container states, network isolation boundaries, database ledgers, and fault-injection behavior—never mock loggers or bypassed checks.
3. **Strict Segregation of Duties:** Strategy research, statistical validation, risk gating, order routing, and telemetry visualization operate across isolated containers and internal Docker networks.

---

## System Architecture

Apex Quant runs as a multi-container stack orchestrated via Docker Compose with internal network segregation (`apex-net` and `risk-net`):

| Service | Container | Role & Responsibilities |
| :--- | :--- | :--- |
| **Risk Engine** | `apex_risk_engine` | FastAPI service (`port 8080`) enforcing portfolio limits, C3 live-trading locks, and HMAC-SHA256 request validation. |
| **Execution Bot** | `apex_bot` | Interfaces with the Alpaca paper-trading API; continuously polls Risk Engine health and enforces fail-closed state transitions. |
| **Researcher Loop** | `apex_researcher` | Executes nightly quantitative research cycles, evaluating Combinatorial Purged Cross-Validation (CPCV), Probability of Backtest Overfitting (PBO), and Deflated Sharpe Ratio (DSR). |
| **Command Terminal** | `apex_app` | Streamlit operator dashboard (`127.0.0.1:8501`, accessible privately via Tailscale) displaying live system telemetry, risk gates, and position readiness. |

### Security & Risk Boundaries
* **Cryptographic Token Boundary (`RSK-02`):** Execution endpoints reject unsigned or tampered payloads (`HTTP 401/403`) using HMAC-SHA256 signature verification.
* **C3 Hard Lock (`RSK-01`):** Live capital deployment is disabled at the environment and engine level (`LIVE_TRADING=False`).
* **C13 Circuit Breaker (`AUT-03`):** SQLite-backed trial ledger tracks consecutive strategy failures and halts autonomous promotion when stop thresholds are breached.
* **Network Isolation (`INF-02` / `INF-03`):** The Streamlit UI binds exclusively to localhost (`127.0.0.1`) behind private Tailscale routing, while the Risk Engine communicates over an internal bridge network (`risk-net`).

---

## Tech Stack

* **Runtime & Infrastructure:** Python 3.12 (`slim` images), Docker, Docker Compose, Ubuntu Linux (Oracle Cloud), Tailscale
* **Backend & Execution:** FastAPI, Uvicorn, Alpaca Trading API
* **Data & Quantitative Analytics:** DuckDB (immutable audit logs), Polars, SQLite (C13 trial ledger), CPCV / DSR / PBO statistical validation
* **Frontend & Observability:** Streamlit, Pytest (fault-injection suite), Dead-Man's Switch heartbeat monitoring

---

## Repository Structure

```text
apex-quant/
├── apex/
│   ├── risk/               # FastAPI Risk Engine, HMAC validation, portfolio limits
│   └── skills/             # Sandboxed research modules (zero direct order-execution access)
├── scripts/
│   ├── nightly_research.py # Autonomous trial runner & statistical evaluation
│   ├── promoter.py         # Automated strategy promotion pipeline
│   └── auto_git_sync.py    # Secret-scanned, event-driven repository synchronization
├── tests/
│   ├── test_risk_limits.py # Portfolio & hard-lock unit tests
│   └── fault_injection/    # 7-point resilience & failure-mode test suite
├── artifacts/              # Generated QA certification reports & trial ledgers (gitignored DBs)
├── app.py                  # Streamlit live telemetry & operator dashboard
├── run_bot.py              # Execution bot & fail-closed risk state machine
├── Apex_Quant_QA.py        # 22-point FRD certification runner
└── docker-compose.yml      # Segregated multi-container orchestration
