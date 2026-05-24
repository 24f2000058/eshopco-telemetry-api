import os
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import numpy as np

app = FastAPI()

# Enable CORS for POST requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# Define request schema
class TelemetryRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

# Resolve path to local telemetry JSON bundle
DATA_PATH = Path(__file__).parent / "telemetry.json"

@app.post("/")
async def get_telemetry_metrics(payload: TelemetryRequest):
    if not DATA_PATH.exists():
        raise HTTPException(status_code=500, detail="Telemetry data bundle missing.")
    
    with open(DATA_PATH, "r") as f:
        telemetry_data = json.load(f)
        
    results = {}
    
    for region in payload.regions:
        # Filter records for the specific region
        region_records = [r for r in telemetry_data if r.get("region") == region]
        
        if not region_records:
            continue
            
        latencies = [r["latency"] for r in region_records if "latency" in r]
        uptimes = [r["uptime"] for r in region_records if "uptime" in r]
        
        if not latencies:
            continue

        # Mathematical calculations
        avg_latency = float(np.mean(latencies))
        p95_latency = float(np.percentile(latencies, 95))
        avg_uptime = float(np.mean(uptimes))
        breaches = int(sum(1 for l in latencies if l > payload.threshold_ms))
        
        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 3),
            "breaches": breaches
        }
        
    return results
