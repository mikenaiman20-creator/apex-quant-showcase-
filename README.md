Apex Quant
 
A paper-trading research platform, built to answer one question honestly: **does any strategy survive proper validation?**
 
> **Status (2026-11-21):** Paper trading only (`LIVE_TRADING=False`). **No strategy has passed validation.** This repository documents the process, including the failures.
> Not financial advice. Nothing here has traded real money.
 
## What this project is
 
- A multi-container system (Docker Compose) with a separated execution bot, risk engine, research worker and operator dashboard.
- A validation pipeline designed to resist the usual retail-quant failure mode: picking the best of many backtests and believing it.
- A record of what was found along the way, including problems in this project's own earlier claims.
## Results so far
 
Data: 16 liquid US stocks/ETFs (Alpaca historical SIP bars, daily, 2016-2025) and BTC/ETH. Development window ends 2025-06-30; the later period is held out and untouched.
 
| Experiment | Candidates tried | Passed the pre-registered gate | Notes |
|---|---|---|---|
| Single-asset trend, SMA-cross and mean-reversion rules (18 symbols) | 630 | **0** | Best deflated Sharpe 0.80 (needs 0.95) |
| Risk-managed trend portfolio on 10 ETFs (inverse-volatility weights, cash when trend is off) | 30 (660 counted cumulatively) | **0** | Net Sharpe 1.07 vs SPY 0.82; max drawdown 13% vs 34%; PBO 0.30, DSR 0.46 |
 
The portfolio result reduced drawdowns but gave up upside, and its Sharpe advantage is not statistically distinguishable from luck at 660 trials. It is a risk-reduction overlay, not an edge. **"No edge established" is the current result.**
 
## Validation approach
 
- **Trial counting:** every candidate is registered (pass, fail or crash) and counted toward the Deflated Sharpe Ratio.
- **Gate (fixed before running):** DSR >= 0.95 and Probability of Backtest Overfitting < 0.20, net of assumed transaction costs.
- **Falsification:** the same pipeline is run on pure random walks and must pass at most 5% of the time. If it does not, no result is trusted.
- **Benchmarks:** compared against SPY buy-and-hold, equal-weight and 60/40.
- **Holdout:** never read during research. A candidate that passes gets one look.
- **Data lineage:** each result records the SHA-256 of the dataset and the git commit.
## Components and honest status
 
| Component | Status |
|---|---|
| Docker stack (bot, risk engine, dashboard) | Running; paper only |
| Real historical data fetch (hashed) | Done |
| Validation module (purged CV, DSR, PBO, gate, trial registry) | Built and unit-tested; being added to this repo |
| Research runs on real data | Done (see results) |
| Execution safeguards (fail-closed behaviour, kill-switch test, reconciliation) | In progress, not yet verified |
| Operator dashboard | Being rewired to real results; may show legacy rows |
| Autonomous LLM hypothesis generator | Not built |
| Heartbeats, alerts, CI | Not built |
 
## Lessons learned
 
- An earlier researcher loop produced simulated results and a dashboard displayed them as if real. It was found, stopped, and replaced with the pipeline above.
- Self-assigned ratings ("9.5/10") were not evidence. They have been removed.
- Secrets hygiene: an exposed monitoring URL was found in the git history and rotated; automated pushes now need a stricter allow-list.
- With hundreds of trials, most "good-looking" strategies are noise. The deflated Sharpe ratio and the noise falsification test are what caught this.
## Roadmap
 
1. Publish the validation module and tests with CI.
2. Honest dashboard fed by the results database.
3. Verify execution safeguards (fail-closed, kill switch, order idempotency, reconciliation).
4. Shadow-track the trend portfolio against SPY (no orders) to collect real out-of-sample data.
 
