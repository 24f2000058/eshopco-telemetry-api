import os
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import numpy as np

app = FastAPI()

# Standard CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS", "GET"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Explicit Preflight/OPTIONS handler for Vercel
@app.options("/{path:path}")
async def preflight_handler(request: Request):
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS, GET"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# Define request schema
class TelemetryRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

# Resolve path to local telemetry JSON bundle
DATA_PATH = Path(__file__).parent / "telemetry.json"

@app.post("/")
async def get_telemetry_metrics(payload: TelemetryRequest, response: Response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    
    if not DATA_PATH.exists():
        raise HTTPException(status_code=500, detail="Telemetry data bundle missing.")
    
    with open(DATA_PATH, "r") as f:
        telemetry_data = json.load(f)
        
    results = {}
    
    for region in payload.regions:
        # Filter records matching the specific region
        region_records = [r for r in telemetry_data if r.get("region") == region]
        
        if not region_records:
            continue
            
        # Extract fields using your exact JSON schema keys: 'latency_ms' and 'uptime_pct'
        latencies = [r["latency_ms"] for r in region_records if "latency_ms" in r]
        uptimes = [r["uptime_pct"] for r in region_records if "uptime_pct" in r]
        
        if not latencies:
            continue

        # Mathematical calculations
        avg_latency = float(np.mean(latencies))
        p95_latency = float(np.percentile(latencies, 95))
        avg_uptime = float(np.mean(uptimes))
        breaches = int(sum(1 for l in latencies if l > payload.threshold_ms))
        
        # Structure fields exactly as needed by the validation check
        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 3),
            "breaches": breaches
        }
        
    return results
