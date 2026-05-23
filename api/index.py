from fastapi import FastAPI
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
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# Define request schema
class TelemetryRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

# --- TELEMETRY DATA REPOSITORY ---
# Replace this placeholder dictionary with your actual sample telemetry bundle data.
# Format: "region_name": [{"latency": 150, "uptime": 1.0}, ...]
TELEMETRY_DATA: Dict[str, List[Dict[str, float]]] = {
    "apac": [
        {"latency": 145.0, "uptime": 1.0},
        {"latency": 160.0, "uptime": 0.99},
        {"latency": 130.0, "uptime": 1.0},
        {"latency": 155.0, "uptime": 1.0}
    ],
    "emea": [
        {"latency": 120.0, "uptime": 1.0},
        {"latency": 180.0, "uptime": 1.0},
        {"latency": 110.0, "uptime": 0.95},
        {"latency": 153.0, "uptime": 1.0}
    ]
}

@app.get("/")
def root():
    return {"status": "healthy", "message": "eShopCo Telemetry API Operational"}

@app.post("/")
def get_metrics(payload: TelemetryRequest):
    response_data = {}
    
    for region in payload.regions:
        # Lowercase incoming string to prevent casing mismatches
        r_key = region.lower()
        
        if r_key not in TELEMETRY_DATA:
            continue
            
        records = TELEMETRY_DATA[r_key]
        latencies = [rec["latency"] for rec in records]
        uptimes = [rec["uptime"] for rec in records]
        
        # Calculate statistical benchmarks
        avg_latency = float(np.mean(latencies))
        p95_latency = float(np.percentile(latencies, 95))
        avg_uptime = float(np.mean(uptimes))
        
        # Count target threshold breaches
        breaches = sum(1 for lat in latencies if lat > payload.threshold_ms)
        
        response_data[region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        }
        
    return response_data
