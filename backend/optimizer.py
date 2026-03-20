import os
import re
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))


def optimize_query(query: str, db_type: str, analysis: dict) -> dict:
    """Rewrite the SQL query using Claude AI and return optimized version + exec plan."""

    issues_text = "\n".join(
        f"- [{i['severity'].upper()}] {i['description']}"
        for i in analysis.get("issues", [])
    )

    prompt = f"""You are a senior DBA. Optimize this {db_type.upper()} SQL query.

ORIGINAL QUERY:
{query}

ISSUES FOUND:
{issues_text}

Return ONLY a JSON object with this exact structure (no markdown, no preamble):
{{
  "optimized_sql": "<rewritten SQL>",
  "exec_plan": [
    {{"type": "scan|index|join|sort|filter", "description": "<detail>"}}
  ],
  "metrics": {{
    "rows_scanned": "<estimate>",
    "index_usage": "<description>",
    "estimated_cost": <number>,
    "join_count": <number>
  }},
  "explanation": "<1-2 sentence summary of changes made>"
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"```json|```", "", raw).strip()

        import json
        result = json.loads(raw)
        return result

    except Exception as e:
        # Fallback: rule-based optimization
        return rule_based_optimize(query, db_type, analysis)


def rule_based_optimize(query: str, db_type: str, analysis: dict) -> dict:
    """Fallback rule-based optimizer when AI is unavailable."""
    q = query.strip()
    issue_codes = [i["code"] for i in analysis.get("issues", [])]

    # Fix SELECT *
    if "SELECT_STAR" in issue_codes:
        q = re.sub(r"SELECT\s+\*", "SELECT /* specify columns here */", q, flags=re.IGNORECASE)

    # Add LIMIT
    if "NO_LIMIT" in issue_codes and "LIMIT" not in q.upper():
        q = q.rstrip(";") + "\nLIMIT 100;"

    # Fix function on column (YEAR/MONTH → BETWEEN)
    if "FUNCTION_ON_COLUMN" in issue_codes:
        q = re.sub(r"YEAR\((\w+)\)\s*=\s*(\d+)", r"\1 BETWEEN '\2-01-01' AND '\2-12-31'", q, flags=re.IGNORECASE)
        q = re.sub(r"MONTH\((\w+)\)\s*=\s*(\d+)", r"/* use date range instead of MONTH() */", q, flags=re.IGNORECASE)

    exec_plan = [
        {"type": "index", "description": "Index seek on primary key"},
        {"type": "join", "description": "Hash join on foreign keys"},
        {"type": "filter", "description": "WHERE clause applied post-join"},
        {"type": "sort", "description": "ORDER BY with index scan"},
    ]

    return {
        "optimized_sql": q,
        "exec_plan": exec_plan,
        "metrics": {
            "rows_scanned": "~200–500",
            "index_usage": "Partial — review manually",
            "estimated_cost": 120.0,
            "join_count": query.upper().count("JOIN"),
        },
        "explanation": "Applied rule-based optimizations. AI rewriting unavailable."
    }
