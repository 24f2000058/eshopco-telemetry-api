from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from pathlib import Path
import json
import numpy as np

app = FastAPI()

# Permissive CORS setup tailored for the grading validation server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Required to be False when using wildcard "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

class TelemetryRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

# Resolve path relative to this file's directory inside Vercel's container
JSON_PATH = Path(__file__).parent / "telemetry.json"

@app.get("/")
def root():
    return {"status": "healthy", "message": "eShopCo JSON-driven Telemetry API"}

@app.post("/")
def get_metrics(payload: TelemetryRequest):
    # 1. Read and parse the raw JSON file directly from the workspace
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        return {"error": f"Failed to load telemetry file: {str(e)}"}

    # 2. Convert incoming request target regions to lowercase set for fast matching
    target_regions = {r.lower() for r in payload.regions}
    
    # 3. Group metrics from the flat list on the fly
    # Structure: {"apac": {"latencies": [...], "uptimes": [...]}}
    grouped_metrics = {r: {"latencies": [], "uptimes": []} for r in target_regions}
    
    for item in raw_data:
        region_item = item.get("region", "").lower()
        if region_item in target_regions:
            # Map keys based on your specific JSON layout
            latency = item.get("latency_ms")
            # If uptime is a percentage (like 97.257), dividing by 100 
            # normalizes it back to standard 0.0-1.0 metric representation.
            uptime = item.get("uptime_pct", 100.0) / 100.0 
            
            if latency is not None:
                grouped_metrics[region_item]["latencies"].append(float(latency))
                grouped_metrics[region_item]["uptimes"].append(float(uptime))

    # 4. Calculate stats for the requested regions
    response_data = {}
    for region in payload.regions:
        r_key = region.lower()
        data = grouped_metrics.get(r_key)
        
        # If a region has no data records, skip it or output empty defaults
        if not data or not data["latencies"]:
            continue
            
        latencies = data["latencies"]
        uptimes = data["uptimes"]
        
        # Run statistical aggregations
        avg_latency = float(np.mean(latencies))
        p95_latency = float(np.percentile(latencies, 95))
        avg_uptime = float(np.mean(uptimes))
        
        # Count values strictly greater than the custom runtime threshold
        breaches = sum(1 for lat in latencies if lat > payload.threshold_ms)
        
        response_data[region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        }
        
    return response_data
