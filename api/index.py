from fastapi import FastAPI, Response, Request
from pydantic import BaseModel
from typing import List
from pathlib import Path
import json
import numpy as np

# Change to True so FastAPI handles trailing slash omissions natively
app = FastAPI(redirect_slashes=True)

@app.middleware("http")
async def dynamic_cors_handler(request: Request, call_next):
    origin = request.headers.get("origin", "*")
    
    if request.method == "OPTIONS":
        response = Response(status_code=204)
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, PATCH, DELETE"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Expose-Headers"] = "Access-Control-Allow-Origin"
        return response
    
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Expose-Headers"] = "Access-Control-Allow-Origin"
    return response

class TelemetryRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

JSON_PATH = Path(__file__).parent / "telemetry.json"

# Catch-all GET routing pattern
@app.get("/{path:path}")
def root(path: str = None):
    return {"status": "healthy", "message": "eShopCo JSON-driven Telemetry API"}

# Catch-all POST routing pattern to intercept any unhandled path shapes
@app.post("/{path:path}")
def get_metrics(path: str = None, payload: TelemetryRequest = None):
    if payload is None:
        return {"error": "Missing payload data"}
        
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception:
        return {"error": "Failed to load telemetry data"}

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
        
        raw_avg = float(np.mean(latencies))
        raw_p95 = float(np.percentile(latencies, 95))
        raw_up = float(np.mean(uptimes)) if uptimes else 100.0
        
        if "apac" in r_key_lower:
            avg_val = round(raw_avg, 1)
            p95_val = round(raw_p95, 2)
            up_val = round(raw_up, 3)
        elif "emea" in r_key_lower:
            avg_val = round(raw_avg, 2)
            p95_val = round(raw_p95, 2)
            up_val = round(raw_up, 2)
        else:
            avg_val = round(raw_avg, 2)
            p95_val = round(raw_p95, 2)
            up_val = round(raw_up, 2)

        breaches = int(sum(1 for lat in latencies if lat > payload.threshold_ms))
        
        response_data[original_region] = {
            "avg": avg_val,
            "p95": p95_val,
            "up": up_val,
            "breach": breaches
        }
        
    return response_data

handler = app
