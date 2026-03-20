from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from analyzer import analyze_query
from optimizer import optimize_query
from safety_validator import validate_safety
from benchmark import benchmark_query
from report_generator import generate_report
from db_connector import get_connection
from history import save_to_history, get_history

app = FastAPI(
    title="SQL Query Optimizer API",
    description="AI-powered SQL query optimization and safety validation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BLOCKED_KEYWORDS = ["DELETE", "DROP", "TRUNCATE", "UPDATE", "INSERT", "ALTER", "GRANT", "REVOKE", "CREATE"]

class QueryRequest(BaseModel):
    query: str
    db_type: str = "postgresql"  # postgresql | mysql
    run_benchmark: bool = False
    generate_pdf: bool = False

class CompareRequest(BaseModel):
    original: str
    optimized: str
    db_type: str = "postgresql"


def is_safe_input(query: str) -> bool:
    upper = query.upper()
    return not any(kw in upper for kw in BLOCKED_KEYWORDS)


@app.get("/")
def root():
    return {"status": "ok", "message": "SQL Optimizer API running"}


@app.post("/analyze")
def analyze(req: QueryRequest):
    if not is_safe_input(req.query):
        raise HTTPException(status_code=400, detail="Only SELECT queries are permitted.")

    analysis = analyze_query(req.query, req.db_type)
    optimized = optimize_query(req.query, req.db_type, analysis)
    safety = validate_safety(req.query, optimized["optimized_sql"], req.db_type)

    result = {
        "original_query": req.query,
        "db_type": req.db_type,
        "score": analysis["score"],
        "issues": analysis["issues"],
        "suggestions": analysis["suggestions"],
        "optimized_sql": optimized["optimized_sql"],
        "exec_plan": optimized["exec_plan"],
        "before_metrics": analysis["metrics"],
        "after_metrics": optimized["metrics"],
        "safety": safety,
        "rows_scanned": analysis["metrics"].get("rows_scanned", "N/A"),
        "index_usage": analysis["metrics"].get("index_usage", "N/A"),
    }

    if req.run_benchmark:
        result["benchmark"] = benchmark_query(req.query, req.db_type)

    save_to_history(result)

    if req.generate_pdf:
        path = generate_report(result)
        result["report_path"] = path

    return result


@app.post("/compare")
def compare(req: CompareRequest):
    if not is_safe_input(req.original) or not is_safe_input(req.optimized):
        raise HTTPException(status_code=400, detail="Only SELECT queries permitted.")

    before = analyze_query(req.original, req.db_type)
    after = analyze_query(req.optimized, req.db_type)
    safety = validate_safety(req.original, req.optimized, req.db_type)
    bench = benchmark_query(req.original, req.db_type, req.optimized)

    return {
        "before": before,
        "after": after,
        "safety": safety,
        "benchmark": bench,
        "improvement": {
            "score_delta": after["score"] - before["score"],
            "time_reduction_pct": bench.get("time_reduction_pct", 0),
        }
    }


@app.get("/history")
def history(limit: int = 20):
    return get_history(limit)


@app.post("/report")
def report(req: QueryRequest):
    if not is_safe_input(req.query):
        raise HTTPException(status_code=400, detail="Only SELECT queries permitted.")
    analysis = analyze_query(req.query, req.db_type)
    optimized = optimize_query(req.query, req.db_type, analysis)
    safety = validate_safety(req.query, optimized["optimized_sql"], req.db_type)
    result = {**analysis, **optimized, "safety": safety, "original_query": req.query}
    path = generate_report(result)
    return {"report_path": path, "message": "Report generated successfully"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
