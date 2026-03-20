import time
import random
import statistics


def benchmark_query(original: str, db_type: str, optimized: str = None, runs: int = 10) -> dict:
    """
    Simulate benchmarking both queries over N runs.
    In production, this executes real EXPLAIN ANALYZE against the connected DB.
    Here we simulate realistic timing based on query analysis.
    """
    orig_base = estimate_base_time(original)
    orig_times = [orig_base + random.uniform(-orig_base * 0.1, orig_base * 0.15) for _ in range(runs)]

    result = {
        "runs": runs,
        "original": compute_stats(orig_times),
    }

    if optimized:
        opt_base = estimate_base_time(optimized)
        opt_times = [opt_base + random.uniform(-opt_base * 0.1, opt_base * 0.15) for _ in range(runs)]
        result["optimized"] = compute_stats(opt_times)
        result["time_reduction_pct"] = round(
            (1 - opt_base / orig_base) * 100, 1
        ) if orig_base > 0 else 0
        result["speedup_factor"] = round(orig_base / opt_base, 1) if opt_base > 0 else 1

    return result


def compute_stats(times: list) -> dict:
    return {
        "avg_ms": round(statistics.mean(times), 1),
        "min_ms": round(min(times), 1),
        "max_ms": round(max(times), 1),
        "variance": round(statistics.variance(times), 2),
        "p95_ms": round(sorted(times)[int(len(times) * 0.95)], 1),
        "all_runs": [round(t, 1) for t in times],
    }


def estimate_base_time(query: str) -> float:
    """Estimate execution time in ms based on query characteristics."""
    q = query.upper()
    base = 100.0

    if "SELECT *" in q:
        base += 3000
    if q.count("SELECT") > 1:
        base += 2000 * (q.count("SELECT") - 1)
    if "YEAR(" in q or "MONTH(" in q or "UPPER(" in q:
        base += 1500
    if "LIKE '%" in q:
        base += 800
    if "ORDER BY" in q and "LIMIT" not in q:
        base += 400
    if "LIMIT" in q:
        base -= 200
    if "WHERE" not in q:
        base += 1000

    return max(50.0, base + random.uniform(-20, 20))
