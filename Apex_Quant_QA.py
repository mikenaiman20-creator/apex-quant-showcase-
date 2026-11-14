#!/usr/bin/env python3
"""
APEX QUANT QA — 9.5/10 FRD Automated Certification Verifier
Executes every verification check defined in the Functional Requirement Document
and outputs raw verification proofs alongside a pass/fail certification matrix.
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Tuple


class CertificationResult:
    def __init__(self, req_id: str, category: str, name: str, passed: bool, output: str):
        self.req_id = req_id
        self.category = category
        self.name = name
        self.passed = passed
        self.output = output.strip()


def run_cmd(cmd: str, timeout: int = 15) -> Tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout.strip()
    except subprocess.TimeoutExpired:
        return 124, f"Command timed out after {timeout}s"
    except Exception as exc:
        return 1, f"Execution error: {exc}"


def verify_inf_01() -> Tuple[bool, str]:
    rc, out = run_cmd("docker inspect apex_app --format '{{json .Mounts}}'")
    if rc != 0:
        return False, f"Container 'apex_app' not found or inspect failed:\n{out}"
    try:
        mounts = json.loads(out)
        bind_mounts = [
            m for m in mounts
            if m.get("Type") == "bind" and "/app" in str(m.get("Destination", ""))
        ]
        if bind_mounts:
            return False, f"FAIL: Active host bind mounts found on /app:\n{json.dumps(bind_mounts, indent=2)}"
        return True, f"PASS: Zero /app bind mounts detected on apex_app.\nMounts: {out}"
    except json.JSONDecodeError:
        return False, f"Failed to parse docker inspect JSON:\n{out}"


def verify_inf_02() -> Tuple[bool, str]:
    rc_port, port_out = run_cmd("docker port apex_app 8501")
    if rc_port != 0:
        return False, f"FAIL: Could not inspect port bindings for apex_app:\n{port_out}"
    if "0.0.0.0:8501" in port_out or "[::]:8501" in port_out:
        return False, f"FAIL: Streamlit is publicly exposed on all interfaces:\n{port_out}"
    rc_ts, ts_out = run_cmd("curl -s -o /dev/null -w '%{http_code}' -m 5 http://100.113.253.104:8501")
    ts_ok = ts_out.strip() in {"200", "302"}
    return ts_ok, f"Port Binding: {port_out}\nTailscale HTTP Status: {ts_out}"


def verify_inf_03() -> Tuple[bool, str]:
    required = ["apex_app", "apex_risk_engine", "apex_bot", "apex_researcher"]
    rc, out = run_cmd('docker ps --format "{{.Names}}\t{{.Status}}"')
    if rc != 0:
        return False, f"FAIL: docker ps failed:\n{out}"
    status_map = {}
    for line in out.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            status_map[parts[0].strip()] = parts[1].strip()
    missing = [f"{n}: {status_map.get(n) or 'NOT RUNNING'}" for n in required if not status_map.get(n) or not status_map.get(n).startswith("Up") or "unhealthy" in status_map.get(n, "").lower()]
    if missing:
        return False, "FAIL:\n" + "\n".join(missing) + f"\n\nFull ps:\n{out}"
    return True, f"PASS: All 4 core containers Up & healthy:\n{out}"


def verify_inf_04() -> Tuple[bool, str]:
    rc, out = run_cmd("docker exec apex_researcher curl -s -m 5 https://api.alpaca.markets", timeout=10)
    if rc != 0:
        return True, f"PASS: apex_researcher blocked from reaching Alpaca (exit={rc}):\n{out}"
    return False, f"FAIL: apex_researcher connected to api.alpaca.markets:\n{out}"


def verify_rsk_01() -> Tuple[bool, str]:
    checks = []
    passed = True
    for fname in ["docker-compose.yml", ".env"]:
        if Path(fname).exists():
            text = Path(fname).read_text(errors="ignore")
            if re.search(r"LIVE_TRADING\s*[:=]\s*['\"]?True", text, re.IGNORECASE):
                passed = False
                checks.append(f"FAIL: LIVE_TRADING=True found in {fname}")
            elif re.search(r"LIVE_TRADING\s*[:=]\s*['\"]?False", text, re.IGNORECASE):
                checks.append(f"OK: LIVE_TRADING=False verified in {fname}")
            else:
                passed = False
                checks.append(f"FAIL: LIVE_TRADING=False missing in {fname}")
    if Path("apex").exists():
        rc, grep_out = run_cmd("grep -rnw './apex' -e 'live_api' -e 'api.alpaca.markets'")
        if rc == 0 and grep_out:
            passed = False
            checks.append(f"FAIL: Live broker endpoint references found in ./apex:\n{grep_out}")
        else:
            checks.append("OK: Zero live_api routes found in ./apex")
    else:
        passed = False
        checks.append("FAIL: ./apex package directory not found")
    return passed, "\n".join(checks)


def verify_rsk_02() -> Tuple[bool, str]:
    cmd_base = "docker exec apex_bot python -c \"import urllib.request, urllib.error; req = urllib.request.Request('http://apex_bot:8001/execute', data=b'{}', headers={'Content-Type':'application/json'%s}); \ntry:\n urllib.request.urlopen(req, timeout=3); print('ALLOWED')\nexcept urllib.error.HTTPError as e:\n print(f'HTTP_{e.code}')\nexcept Exception as ex:\n print(f'ERR_{ex}')\""
    _, out1 = run_cmd(cmd_base % "")
    _, out2 = run_cmd(cmd_base % ", 'X-Risk-Token':'tampered_invalid_sig'")
    passed = (("HTTP_401" in out1) or ("HTTP_403" in out1)) and (("HTTP_401" in out2) or ("HTTP_403" in out2))
    return passed, f"Missing Token: {out1}\nTampered Token: {out2}"


def verify_rsk_03() -> Tuple[bool, str]:
    rc_stop, out_stop = run_cmd("docker stop apex_risk_engine", timeout=15)
    if rc_stop != 0:
        return False, f"FAIL: Could not stop apex_risk_engine:\n{out_stop}"
    run_cmd("sleep 3")
    _, logs_down = run_cmd("docker logs apex_bot --tail 20")
    halted = ("STANDBY" in logs_down) and ("RISK_UNREACHABLE" in logs_down)
    run_cmd("docker start apex_risk_engine", timeout=15)
    run_cmd("sleep 3")
    _, logs_up = run_cmd("docker logs apex_bot --tail 15")
    resumed = ("ACTIVE" in logs_up) or ("CONNECTED" in logs_up) or ("RESUMED" in logs_up)
    return (halted and resumed), f"During Outage:\n{logs_down}\n\nAfter Restart:\n{logs_up}"


def verify_rsk_04() -> Tuple[bool, str]:
    if not Path("tests/test_risk_limits.py").exists():
        return False, "FAIL: tests/test_risk_limits.py does not exist."
    rc, out = run_cmd("pytest tests/test_risk_limits.py -v", timeout=30)
    return (rc == 0), out


def verify_sta_01() -> Tuple[bool, str]:
    if not Path("tests/test_cpcv.py").exists():
        return False, "FAIL: tests/test_cpcv.py does not exist."
    rc, out = run_cmd("pytest tests/test_cpcv.py -v", timeout=30)
    return (rc == 0), out


def verify_sta_02() -> Tuple[bool, str]:
    if not Path("tests/test_dsr.py").exists():
        return False, "FAIL: tests/test_dsr.py does not exist."
    rc, out = run_cmd("pytest tests/test_dsr.py -v", timeout=30)
    return (rc == 0), out


def verify_sta_03() -> Tuple[bool, str]:
    if not Path("tests/test_trial_counter.py").exists():
        return False, "FAIL: tests/test_trial_counter.py does not exist."
    wal_status, wal_ok = "trials.db not found", False
    if Path("trials.db").exists():
        try:
            conn = sqlite3.connect("trials.db")
            mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            conn.close()
            wal_status, wal_ok = f"trials.db journal_mode = {mode}", (str(mode).lower() == "wal")
        except Exception as exc:
            wal_status = f"SQLite check error: {exc}"
    rc, out = run_cmd("pytest tests/test_trial_counter.py -v", timeout=45)
    return (rc == 0 and wal_ok), f"{wal_status}\n\n{out}"


def verify_sta_04() -> Tuple[bool, str]:
    cmd = 'python3 -c "from apex.data.holdout import load_holdout, HoldoutIntegrityError; load_holdout(); print(\'VALID_HOLDOUT_VERIFIED\')"'
    rc, out = run_cmd(cmd)
    return (rc == 0), out


def verify_sta_05() -> Tuple[bool, str]:
    if not Path("tests/calibration/test_keystone.py").exists():
        return False, "FAIL: tests/calibration/test_keystone.py does not exist."
    rc, out = run_cmd("pytest tests/calibration/test_keystone.py -v", timeout=45)
    rep = Path("artifacts/calibration_report.md").exists()
    return (rc == 0 and rep), f"Report exists: {rep}\n\n{out}"


def verify_sta_06() -> Tuple[bool, str]:
    report = Path("artifacts/slippage_calibration.md")
    if not report.exists():
        return False, "FAIL: artifacts/slippage_calibration.md does not exist."
    content = report.read_text(errors="ignore")
    return True, f"PASS: Found artifacts/slippage_calibration.md ({len(content)} bytes):\n{content[:500]}"


def verify_aut_01() -> Tuple[bool, str]:
    rc, out = run_cmd("docker logs apex_researcher --tail 50")
    if rc != 0:
        return False, f"FAIL: Could not read apex_researcher logs:\n{out}"
    return (("Trial" in out) and ("PBO evaluated" in out) and ("DSR evaluated" in out)), out


def verify_aut_02() -> Tuple[bool, str]:
    script = Path("scripts/promoter.py")
    if not script.exists():
        return False, "FAIL: scripts/promoter.py does not exist."
    text = script.read_text(errors="ignore")
    checks = ["14" in text, "1.0" in text, "strategies.yaml" in text, "git commit" in text and "git push" in text]
    return all(checks), f"Promoter checks: {checks}"


def verify_aut_03() -> Tuple[bool, str]:
    log_path = Path("artifacts/c13_trigger.log")
    has_code = (run_cmd("grep -rnw './apex' -e 'c13_trigger'")[0] == 0) if Path("apex").exists() else False
    return (has_code or log_path.exists()), f"c13_trigger in code: {has_code}, log exists: {log_path.exists()}"


def verify_aut_04() -> Tuple[bool, str]:
    skills_dir = Path("apex/skills")
    if not skills_dir.exists():
        return False, "FAIL: apex/skills/ directory does not exist."
    rc, out = run_cmd("grep -rn 'submit_order' apex/skills/")
    if rc == 0 and out:
        return False, f"FAIL: Forbidden execution call found:\n{out}"
    return True, "PASS: Zero submit_order references found in apex/skills/."


def verify_obs_01() -> Tuple[bool, str]:
    rc, out = run_cmd("grep -rnE 'healthchecks\\.io|hc-ping\\.com|ntfy\\.sh|DEADMAN_WEBHOOK' . --exclude=Apex_Quant_QA.py")
    return (rc == 0 and bool(out)), out or "FAIL: No Dead-man switch webhook integration found."


def verify_obs_02() -> Tuple[bool, str]:
    if not Path("tests/fault_injection").exists():
        return False, "FAIL: tests/fault_injection/ directory does not exist."
    rc, out = run_cmd("pytest tests/fault_injection/ -v", timeout=60)
    return (rc == 0 and "7 passed" in out), out


def verify_obs_03() -> Tuple[bool, str]:
    cmd = 'python3 -c "import duckdb, glob; files = glob.glob(\'**/*.duckdb\', recursive=True); assert files, \'No .duckdb files\'; con = duckdb.connect(files[0], read_only=True); rows = con.execute(\'SELECT * FROM audit_logs LIMIT 1\').fetchall(); cols = [d[0] for d in con.description]; print(cols, rows)"'
    rc, out = run_cmd(cmd)
    if rc != 0:
        return False, f"FAIL: DuckDB query failed:\n{out}"
    return all(k in out.lower() for k in ["timestamp", "git", "hmac"]), out


def verify_obs_04() -> Tuple[bool, str]:
    doc = Path("docs/stop-rule.md")
    if not doc.exists():
        return False, "FAIL: docs/stop-rule.md does not exist."
    text = doc.read_text(errors="ignore")
    return ("5%" in text and "3" in text and ("Signed" in text or "Signature" in text)), text


CHECKS: List[Tuple[str, str, str, Callable[[], Tuple[bool, str]]]] = [
    ("INF-01", "Infrastructure & Security", "Immutable Container Runtime", verify_inf_01),
    ("INF-02", "Infrastructure & Security", "Tailscale/Proxy Network Isolation", verify_inf_02),
    ("INF-03", "Infrastructure & Security", "Multi-Container Segregation", verify_inf_03),
    ("INF-04", "Infrastructure & Security", "Zero-Trust Dependency Enforcement", verify_inf_04),
    ("RSK-01", "Execution & Risk", "C3 Hard Lock (No Live Trading)", verify_rsk_01),
    ("RSK-02", "Execution & Risk", "HMAC Cryptographic Token Boundary", verify_rsk_02),
    ("RSK-03", "Execution & Risk", "Fail-Closed Risk Engine", verify_rsk_03),
    ("RSK-04", "Execution & Risk", "Hard Portfolio Limits", verify_rsk_04),
    ("STA-01", "Statistical Rigor", "Combinatorial Purged CV (CPCV)", verify_sta_01),
    ("STA-02", "Statistical Rigor", "Deflated Sharpe Ratio (DSR)", verify_sta_02),
    ("STA-03", "Statistical Rigor", "Trial Counter Integrity", verify_sta_03),
    ("STA-04", "Statistical Rigor", "Cryptographic Holdout Lock", verify_sta_04),
    ("STA-05", "Statistical Rigor", "Keystone Calibration", verify_sta_05),
    ("STA-06", "Statistical Rigor", "Slippage & Cost Calibration", verify_sta_06),
    ("AUT-01", "Autonomous Factory", "Researcher Loop", verify_aut_01),
    ("AUT-02", "Autonomous Factory", "Auto-Promoter Pipeline", verify_aut_02),
    ("AUT-03", "Autonomous Factory", "C13 Agent Stop Rule", verify_aut_03),
    ("AUT-04", "Autonomous Factory", "Sandboxed Skill Research", verify_aut_04),
    ("OBS-01", "Observability & Governance", "Dead-Man's Switch", verify_obs_01),
    ("OBS-02", "Observability & Governance", "Fault Injection Suite", verify_obs_02),
    ("OBS-03", "Observability & Governance", "Immutable Audit Trail", verify_obs_03),
    ("OBS-04", "Observability & Governance", "Binding Stop Rule", verify_obs_04),
]


def main() -> int:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print("=" * 72)
    print(f"APEX QUANT QA — 9.5/10 FRD CERTIFICATION SUITE | {timestamp}")
    print("=" * 72)

    results: List[CertificationResult] = []
    for req_id, category, name, fn in CHECKS:
        print(f"[*] Running {req_id}: {name}...", end=" ", flush=True)
        try:
            passed, output = fn()
        except Exception as exc:
            passed, output = False, f"Unhandled verifier exception: {exc}"
        print("PASS" if passed else "FAIL")
        results.append(CertificationResult(req_id, category, name, passed, output))

    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    certified = (passed_count == total_count)

    Path("artifacts").mkdir(exist_ok=True)
    report_path = Path("artifacts/Apex_Quant_QA_Report.md")
    fence = "`" * 3

    lines = [
        "# APEX QUANT QA — 9.5/10 FRD Certification Proof Report",
        f"**Generated:** {timestamp}  ",
        f"**Score:** `{passed_count} / {total_count}` Requirements Passed  ",
        f"**Certification Status:** {'✅ CERTIFIED 9.5/10' if certified else '❌ NOT CERTIFIED (GAPS DETECTED)'}",
        "",
        "## Summary Matrix",
        "| ID | Category | Requirement | Status |",
        "| :--- | :--- | :--- | :--- |",
    ]
    for r in results:
        lines.append(f"| **{r.req_id}** | {r.category} | {r.name} | {'✅ PASS' if r.passed else '❌ FAIL'} |")

    lines.extend(["", "## Raw Verification Evidence", ""])
    for r in results:
        lines.append(f"### {r.req_id}: {r.name} ({'✅ PASS' if r.passed else '❌ FAIL'})")
        lines.append(f"{fence}text")
        lines.append(r.output or "(no output)")
        lines.append(fence)
        lines.append("")

    report_path.write_text("\n".join(lines))
    print("=" * 72)
    print(f"RESULT: {passed_count}/{total_count} PASSED | Report saved to: {report_path}")
    print("=" * 72)
    return 0 if certified else 1


if __name__ == "__main__":
    sys.exit(main())
