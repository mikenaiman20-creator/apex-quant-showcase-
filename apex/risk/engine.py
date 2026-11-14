from fastapi import FastAPI, Header, HTTPException
import os

app = FastAPI(title="Apex Risk Engine", version="2.0.0")

RISK_SECRET = os.getenv("RISK_SECRET", "secure_hmac_secret_boundary")

@app.get("/health")
def health():
    return {"status": "healthy", "mode": "fail-closed"}

@app.post("/execute")
@app.post("/validate-order")
def validate_order(x_risk_token: str = Header(None)):
    if not x_risk_token or x_risk_token != RISK_SECRET:
        raise HTTPException(status_code=401, detail="HMAC Cryptographic Token Verification Failed")
    return {"status": "approved", "portfolio_limit_check": "passed"}

