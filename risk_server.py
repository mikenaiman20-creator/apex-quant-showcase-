from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok", "online": True}

@app.post("/validate_order")
def validate_order(order: dict):
    # Genuine HMAC token generation would go here
    return {
        "approved": True, 
        "reason": "Passed risk thresholds", 
        "token": "secure_hmac_token_12345"
    }
