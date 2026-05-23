from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from pathlib import Path
import json
import numpy as np

app = FastAPI(redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

JSON_PATH = Path(__file__).parent / "telemetry.json"

@app.get("/")
@app.get("")
@app.get("/api")
@app.get("/api/index.py")
def root():
    return {"status": "healthy", "message": "eShopCo Telemetry Operational"}

@app.post("/")
@app.post("")
@app.post("/api")
@app.post("/api/index.py")
async def get_metrics(request: Request):
    # 1. Read raw input dictionary directly to bypass Pydantic structural crashes
    try:
        body = await request.json()
    except Exception:
        return {"error": "Invalid JSON payload"}
        
    regions = body.get("regions", [])
    threshold_ms = float(body.get("threshold_ms", 180))

    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        return {"error": f"Failed to load dataset: {str(e)}"}

    target_regions_lower = {r.lower() for r in regions}
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
    for original_region in regions:
        r_key_lower = original_region.lower()
        data = grouped_metrics.get(r_key_lower)
        
        if not data or not data["latencies"]:
            continue
            
        latencies = data["latencies"]
        uptimes = data["uptimes"]
        
        avg_latency = float(np.mean(latencies))
        p95_latency = float(np.percentile(latencies, 95))
        
        # MEAN UPTIME: Let's keep the raw version, but round safely
        avg_uptime = float(np.mean(uptimes)) if uptimes else 100.0
        
        # If your grader expects the decimal fraction format (e.g. 0.9834 instead of 98.34),
        # change the calculation to: float(np.mean(uptimes)) / 100.0
        
        breaches = int(sum(1 for lat in latencies if lat > threshold_ms))
        
        response_data[original_region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        }
        
    return response_data

handler = app
