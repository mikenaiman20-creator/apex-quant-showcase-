import time
import os
import requests
import structlog
from fastapi import FastAPI, Header, HTTPException
import uvicorn
import threading

logger = structlog.get_logger()
app = FastAPI()
STATE = "INITIALIZING"
RISK_TOKEN = "secure_hmac_token_12345"

@app.post("/execute")
def execute_order(x_risk_token: str = Header(None)):
    if not x_risk_token or x_risk_token != RISK_TOKEN:
        raise HTTPException(status_code=401, detail="Missing or invalid HMAC token")
    return {"status": "executed"}

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="warning")

def check_requirements():
    if os.getenv("LIVE_TRADING", "true").lower() != "false":
        return False
    try:
        res = requests.get("http://apex_risk_engine:8080/health", timeout=3)
        if res.status_code != 200:
            logger.warning("RISK_UNREACHABLE: Risk engine returned non-200")
            return False
    except Exception as e:
        logger.warning(f"RISK_UNREACHABLE: {e}")
        return False
    return True

def monitor_loop():
    global STATE
    logger.info("Bot initialized. Entering STANDBY mode.")
    STATE = "STANDBY"
    while True:
        if check_requirements():
            if STATE == "STANDBY":
                STATE = "ACTIVE"
                logger.info("ACTIVE: All requirements met. Paper trading enabled.")
        else:
            if STATE == "ACTIVE":
                STATE = "STANDBY"
                logger.warning("STANDBY: Dependency failed. Orders blocked.")
        time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    monitor_loop()
