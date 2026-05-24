import os
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import numpy as np

app = FastAPI()

# 1. Standard CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False if allow_origins is ["*"]
    allow_methods=["POST", "OPTIONS", "GET"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 2. Explicit Preflight/OPTIONS handler for Vercel Serverless environment
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
    # Ensure the actual POST response also explicitly injects the wildcard header
    response.headers["Access-Control-Allow-Origin"] = "*"
    
    if not DATA_PATH.exists():
        raise HTTPException(status_code=500, detail="Telemetry data bundle missing.")
    
    with open(DATA_PATH, "r") as f:
        telemetry_data = json.load(f)
        
    results = {}
    
    for region in payload.regions:
        region_records = [r for r in telemetry_data if r.get("region") == region]
        
        if not region_records:
            continue
            
        latencies = [r["latency"] for r in region_records if "latency" in r]
        uptimes = [r["uptime"] for r in region_records if "uptime" in r]
        
        if not latencies:
            continue

        # Calculations
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
