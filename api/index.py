from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from pathlib import Path
import json
import numpy as np

app = FastAPI(redirect_slashes=False)

# FIX: Explicitly grant full permission modifiers inside the middleware
# to ensure POST payloads bypass browser sandboxes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],  # Crucial for POST/OPTIONS
    allow_headers=["*"],  # Crucial for Content-Type
)

class TelemetryRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

JSON_PATH = Path(__file__).parent / "telemetry.json"

@app.get("/")
@app.get("")
def root():
    return {"status": "healthy", "message": "eShopCo JSON-driven Telemetry API"}

@app.post("/")
@app.post("")
def get_metrics(payload: TelemetryRequest):
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        return {"error": f"Failed to load telemetry file: {str(e)}"}

    target_regions_lower = {r.lower() for r in payload.regions}
    grouped_metrics = {r: {"latencies": [], "uptimes": []} for r in target_regions_lower}
    
    for item in raw_data:
        region_item = item.get("region", "").lower()
        if region_item in target_regions_lower:
            latency = item.get("latency_ms")
            uptime = item.get("uptime_pct") 
            
            if latency is not None:
                grouped_metrics[region_item]["latencies"].append(float(latency))
            if uptime is not None:
                grouped_metrics[region_item]["uptimes"].append(float(uptime))

    response_data = {}
    for original_region in payload.regions:
        r_key_lower = original_region.lower()
        data = grouped_metrics.get(r_key_lower)
        
        if not data or not data["latencies"]:
            continue
            
        latencies = data["latencies"]
        uptimes = data["uptimes"]
        
        avg_latency = round(float(np.mean(latencies)), 4)
        p95_latency = round(float(np.percentile(latencies, 95)), 4)
        avg_uptime = round(float(np.mean(uptimes)), 4) if uptimes else 100.0
        
        breaches = int(sum(1 for lat in latencies if lat > payload.threshold_ms))
        
        response_data[original_region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        }
        
    return response_data

handler = app
