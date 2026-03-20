import re
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where
from sqlparse.tokens import Keyword, DML


def analyze_query(query: str, db_type: str = "postgresql") -> dict:
    issues = []
    suggestions = []
    score = 100

    parsed = sqlparse.parse(query.strip())[0]
    query_upper = query.upper()

    # ── RULE 1: SELECT * ──────────────────────────────────────────
    if re.search(r"SELECT\s+\*", query_upper):
        issues.append({"severity": "critical", "code": "SELECT_STAR",
                       "description": "SELECT * fetches all columns. Use explicit column names."})
        suggestions.append({"title": "Replace SELECT *",
                             "detail": "List only required columns: SELECT id, name, email FROM ..."})
        score -= 25

    # ── RULE 2: Missing WHERE clause ──────────────────────────────
    if "WHERE" not in query_upper and "JOIN" not in query_upper:
        issues.append({"severity": "critical", "code": "NO_WHERE",
                       "description": "No WHERE clause — full table scan will be performed."})
        suggestions.append({"title": "Add WHERE clause",
                             "detail": "Filter rows at DB level to reduce rows scanned."})
        score -= 20

    # ── RULE 3: Missing LIMIT ─────────────────────────────────────
    if "LIMIT" not in query_upper:
        issues.append({"severity": "warning", "code": "NO_LIMIT",
                       "description": "No LIMIT clause — query may return millions of rows."})
        suggestions.append({"title": "Add LIMIT clause",
                             "detail": "Always paginate: LIMIT 100 OFFSET 0"})
        score -= 10

    # ── RULE 4: Correlated / nested subqueries ────────────────────
    subquery_count = query_upper.count("SELECT") - 1
    if subquery_count > 0:
        issues.append({"severity": "critical", "code": "NESTED_SUBQUERY",
                       "description": f"{subquery_count} nested subquery(s) detected — N+1 risk."})
        suggestions.append({"title": "Replace subqueries with JOINs",
                             "detail": "Use LEFT JOIN + GROUP BY instead of correlated SELECT inside SELECT."})
        score -= 20 * subquery_count

    # ── RULE 5: Function on column (index killer) ─────────────────
    func_patterns = [r"YEAR\(", r"MONTH\(", r"DATE\(", r"UPPER\(", r"LOWER\(", r"CAST\("]
    for pat in func_patterns:
        if re.search(pat, query_upper):
            issues.append({"severity": "critical", "code": "FUNCTION_ON_COLUMN",
                           "description": f"Function used on column ({pat[:-2]}) — prevents index usage."})
            suggestions.append({"title": "Remove function from column",
                                 "detail": f"Instead of {pat[:-2]}(col) = val, use col BETWEEN range to keep index."})
            score -= 20
            break

    # ── RULE 6: LIKE with leading wildcard ────────────────────────
    if re.search(r"LIKE\s+'%", query_upper):
        issues.append({"severity": "warning", "code": "LEADING_WILDCARD",
                       "description": "LIKE '%value' with leading wildcard disables index scans."})
        suggestions.append({"title": "Avoid leading wildcard",
                             "detail": "Use full-text search (GIN index in PostgreSQL) or LIKE 'value%' where possible."})
        score -= 15

    # ── RULE 7: Implicit Cartesian JOIN ──────────────────────────
    if re.search(r"FROM\s+\w+\s+\w+\s*,\s*\w+", query_upper) or \
       (query_upper.count("FROM") == 1 and "," in query.split("FROM")[1].split("WHERE")[0] and "JOIN" not in query_upper):
        issues.append({"severity": "critical", "code": "CARTESIAN_JOIN",
                       "description": "Implicit comma-separated tables create a Cartesian product."})
        suggestions.append({"title": "Use explicit JOIN syntax",
                             "detail": "Replace 'FROM a, b WHERE a.id = b.id' with 'FROM a INNER JOIN b ON a.id = b.id'."})
        score -= 30

    # ── RULE 8: ORDER BY on non-indexed column ────────────────────
    if re.search(r"ORDER\s+BY", query_upper):
        issues.append({"severity": "info", "code": "ORDER_BY_CHECK",
                       "description": "ORDER BY detected — verify the column is indexed to avoid filesort."})
        score -= 5

    # ── RULE 9: OR conditions ─────────────────────────────────────
    if re.search(r"\bOR\b", query_upper):
        issues.append({"severity": "warning", "code": "OR_CONDITION",
                       "description": "OR conditions can prevent index usage. Consider UNION or IN()."})
        score -= 5

    # ── Score floor ───────────────────────────────────────────────
    score = max(0, score)

    # ── Estimate metrics ──────────────────────────────────────────
    rows_scanned = estimate_rows(query_upper, score)
    index_usage = estimate_index_usage(query_upper, issues)

    return {
        "score": score,
        "issues": issues,
        "suggestions": suggestions,
        "metrics": {
            "rows_scanned": rows_scanned,
            "index_usage": index_usage,
            "estimated_cost": round((100 - score) * 42.5, 1),
            "join_count": query_upper.count("JOIN"),
            "subquery_count": subquery_count,
        }
    }


def estimate_rows(query_upper: str, score: int) -> str:
    if score < 30:
        return "~50,000+"
    elif score < 60:
        return "~5,000–20,000"
    elif score < 80:
        return "~500–2,000"
    else:
        return "~50–500"


def estimate_index_usage(query_upper: str, issues: list) -> str:
    critical = [i for i in issues if i["severity"] == "critical"]
    join_count = query_upper.count("JOIN")
    if not critical:
        return f"{join_count}/{join_count} joins indexed" if join_count else "Full index hit"
    return f"0/{join_count} joins indexed" if join_count else "No index used"
