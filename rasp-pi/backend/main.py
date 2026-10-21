from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from shared.models import engine, SystemMetric
import json
from pydantic import BaseModel
import subprocess
from typing import Optional
import time
import os

app = FastAPI()

class WiFiCredentials(BaseModel):
    ssid: str
    password: Optional[str] = ""

@app.post("/api/connect-wifi")
def connect_wifi(creds: WiFiCredentials):
    request_file = "/app/host_data/connect_request.json"
    result_file = "/app/host_data/connect_result.json"

    if os.path.exists(result_file):
        os.remove(result_file)
    
    with open(request_file, 'w') as f:
        json.dump({"ssid": creds.ssid, "password": creds.password}, f)

    start_time = time.time()
    while time.time() - start_time < 20:
        if os.path.exists(result_file):
            with open(result_file, 'r') as f:
                result = json.load(f)
            
            os.remove(result_file)

            if result.get("success"):
                return {"success": True, "message": "Successfully connected."}
            else:
                raise HTTPException(status_code=400, detail=result.get("error", "Failed to connect"))
            
        time.sleep(1)
    
    if os.path.exists(request_file):
        os.remove(request_file)
    raise HTTPException(status_code=504, detail="Host connection script timed out")

@app.get("/api/metrics/latest")
def get_latest_metric():
    with Session(engine) as db:
        # Fetch the most recent db entry and return
        latest = db.query(SystemMetric).order_by(SystemMetric.id.desc()).first()
        return latest

@app.get("/api/metrics/dc1")
def get_dc1():
    # Grab all values with location 2, i.e., in the dc1 output
    with Session(engine) as db:
        statement = select(SystemMetric).where(SystemMetric.value_location == 1).order_by(desc(SystemMetric.id)).limit(50)
        values = db.execute(statement).scalars().all()[::-1]
        return values

@app.get("/api/metrics/batt")
def get_batt():
    # Grab all values with location 2, i.e., in the dc1 output
    with Session(engine) as db:
        statement = select(SystemMetric).where(SystemMetric.value_location == 2).order_by(desc(SystemMetric.id)).limit(50)
        values = db.execute(statement).scalars().all()[::-1]
        return values

@app.get("/api/network-status")
def check_network_status():
    try:
        with open('/app/host_data/status.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"connected": False, "ssid": None}

