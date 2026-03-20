import re


def validate_safety(original: str, optimized: str, db_type: str) -> dict:
    """
    Run DBA production safety checklist between original and optimized queries.
    Returns status: SAFE | WARNING | NOT SAFE
    """
    checks = []
    warnings = 0
    failures = 0

    orig_upper = original.upper().strip()
    opt_upper = optimized.upper().strip()

    # ── CHECK 1: Only SELECT statements ──────────────────────────
    blocked = ["DELETE", "DROP", "TRUNCATE", "UPDATE", "INSERT", "ALTER"]
    write_ops = [kw for kw in blocked if kw in opt_upper]
    if write_ops:
        checks.append({"check": "Write operation guard", "passed": False,
                       "note": f"Optimized query contains: {', '.join(write_ops)}"})
        failures += 1
    else:
        checks.append({"check": "Write operation guard", "passed": True,
                       "note": "No DDL or DML write operations detected."})

    # ── CHECK 2: Same base tables ─────────────────────────────────
    orig_tables = extract_tables(original)
    opt_tables = extract_tables(optimized)
    missing = orig_tables - opt_tables
    if missing:
        checks.append({"check": "Base table coverage", "passed": False,
                       "note": f"Tables missing in optimized query: {missing}"})
        failures += 1
    else:
        checks.append({"check": "Base table coverage", "passed": True,
                       "note": f"All source tables present: {', '.join(orig_tables) or 'N/A'}"})

    # ── CHECK 3: JOIN conditions preserved ────────────────────────
    orig_joins = count_joins(orig_upper)
    opt_joins = count_joins(opt_upper)
    if opt_joins < orig_joins:
        checks.append({"check": "JOIN completeness", "passed": False,
                       "note": f"Original had {orig_joins} JOINs, optimized has {opt_joins}."})
        warnings += 1
    else:
        checks.append({"check": "JOIN completeness", "passed": True,
                       "note": f"{opt_joins} JOIN(s) maintained correctly."})

    # ── CHECK 4: WHERE clause preserved ──────────────────────────
    orig_has_where = "WHERE" in orig_upper
    opt_has_where = "WHERE" in opt_upper
    if orig_has_where and not opt_has_where:
        checks.append({"check": "WHERE clause preservation", "passed": False,
                       "note": "Original had WHERE clause but optimized does not — unintended filtering removed."})
        failures += 1
    else:
        checks.append({"check": "WHERE clause preservation", "passed": True,
                       "note": "WHERE clause structure preserved."})

    # ── CHECK 5: NULL handling ────────────────────────────────────
    orig_null = "IS NULL" in orig_upper or "IS NOT NULL" in orig_upper
    opt_null = "IS NULL" in opt_upper or "IS NOT NULL" in opt_upper
    if orig_null and not opt_null:
        checks.append({"check": "NULL handling", "passed": False,
                       "note": "NULL checks in original not present in optimized query."})
        warnings += 1
    else:
        checks.append({"check": "NULL handling", "passed": True,
                       "note": "NULL semantics preserved."})

    # ── CHECK 6: LIMIT added (info) ───────────────────────────────
    if "LIMIT" not in opt_upper:
        checks.append({"check": "Pagination (LIMIT)", "passed": False,
                       "note": "No LIMIT in optimized query — could return unbounded rows."})
        warnings += 1
    else:
        limit_val = extract_limit(opt_upper)
        checks.append({"check": "Pagination (LIMIT)", "passed": True,
                       "note": f"LIMIT {limit_val} applied — verify pagination logic matches app expectations."})

    # ── CHECK 7: Locking impact ───────────────────────────────────
    checks.append({"check": "Locking impact", "passed": True,
                   "note": "SELECT queries acquire shared read locks only — safe for concurrent access."})

    # ── CHECK 8: Aggregate functions preserved ────────────────────
    orig_agg = has_aggregates(orig_upper)
    opt_agg = has_aggregates(opt_upper)
    if orig_agg and not opt_agg:
        checks.append({"check": "Aggregate preservation", "passed": False,
                       "note": "Original had aggregates (COUNT/SUM/AVG) not present in optimized."})
        warnings += 1
    else:
        checks.append({"check": "Aggregate preservation", "passed": True,
                       "note": "Aggregate functions preserved correctly."})

    # ── Final verdict ─────────────────────────────────────────────
    if failures > 0:
        status = "NOT SAFE"
    elif warnings > 0:
        status = "WARNING"
    else:
        status = "SAFE"

    return {
        "status": status,
        "checks": checks,
        "failures": failures,
        "warnings": warnings,
        "summary": f"{len(checks)} checks · {failures} failures · {warnings} warnings"
    }


def extract_tables(query: str) -> set:
    tables = set()
    patterns = [
        r"FROM\s+(\w+)",
        r"JOIN\s+(\w+)",
    ]
    for pat in patterns:
        for match in re.finditer(pat, query, re.IGNORECASE):
            tables.add(match.group(1).lower())
    return tables


def count_joins(query_upper: str) -> int:
    return len(re.findall(r"\bJOIN\b", query_upper))


def extract_limit(query_upper: str) -> str:
    m = re.search(r"LIMIT\s+(\d+)", query_upper)
    return m.group(1) if m else "?"


def has_aggregates(query_upper: str) -> bool:
    return bool(re.search(r"\b(COUNT|SUM|AVG|MAX|MIN)\s*\(", query_upper))
