# ⚡ QueryLens — SQL Query Optimization Analyzer

> AI-powered SQL analysis, production safety validation, benchmarking & PDF report generation.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35-FF4B4B?style=flat)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat)](https://python.org)

---

## 🎯 What It Does

- Accepts any SQL SELECT query
- Detects 9+ anti-patterns (SELECT *, missing indexes, bad JOINs, etc.)
- Scores query 0–100 and explains why
- Rewrites the query using Claude AI
- Validates production safety with 8-point DBA checklist
- Benchmarks original vs optimized (10 runs)
- Generates downloadable PDF reports
- Stores full audit history in SQLite

---

## 📁 Project Structure

```
sql-optimizer/
├── backend/
│   ├── app.py               ← FastAPI main + all routes
│   ├── analyzer.py          ← SQL anti-pattern detection engine
│   ├── optimizer.py         ← AI query rewriter (Claude API)
│   ├── safety_validator.py  ← 8-point production safety checker
│   ├── benchmark.py         ← Multi-run performance benchmarking
│   ├── db_connector.py      ← PostgreSQL + MySQL connector
│   ├── history.py           ← SQLite audit log
│   ├── report_generator.py  ← ReportLab PDF generator
│   └── requirements.txt
├── frontend/
│   ├── app.py               ← Streamlit multi-page dashboard
│   ├── requirements.txt
│   └── .streamlit/
│       └── secrets.toml.example
├── database/
│   ├── schema.sql           ← E-commerce tables + indexes
│   └── sample_data.sql      ← Sample data + slow query test cases
├── reports/
│   └── generated/           ← PDF reports saved here
├── render.yaml              ← Render.com deployment config
└── README.md
```

---

## 🚀 Local Setup

### 1. Clone & install

```bash
git clone https://github.com/yourname/sql-optimizer
cd sql-optimizer

# Backend
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy env
cp .env.example .env
# Edit .env with your keys
```

### 2. Set environment variables

```env
ANTHROPIC_API_KEY=sk-ant-...
POSTGRES_URL=postgresql://user:pass@host:5432/db?sslmode=require
MYSQL_URL=mysql+pymysql://user:pass@host/db
```

### 3. Start backend

```bash
cd backend
uvicorn app:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### 4. Start frontend

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
# Opens: http://localhost:8501
```

### 5. Load sample data (optional)

```bash
psql $POSTGRES_URL -f database/schema.sql
psql $POSTGRES_URL -f database/sample_data.sql
```

---

## 🌐 Free Deployment

| Component   | Service          | Free Tier         |
|-------------|------------------|-------------------|
| Frontend    | Streamlit Cloud  | Unlimited apps    |
| Backend API | Render.com       | 512MB RAM, sleeps |
| PostgreSQL  | Neon             | 0.5GB, serverless |
| MySQL       | PlanetScale      | 5GB hobby plan    |
| History DB  | SQLite on Render | Included          |

### Deploy Backend → Render

1. Push to GitHub
2. Go to render.com → New Web Service
3. Connect repo, set Root Dir: `backend`
4. Build: `pip install -r requirements.txt`
5. Start: `uvicorn app:app --host 0.0.0.0 --port $PORT`
6. Add env vars in Render dashboard

### Deploy Frontend → Streamlit Cloud

1. Go to share.streamlit.io
2. New app → select repo → `frontend/app.py`
3. Add secrets: `API_URL = "https://yourapp.onrender.com"`

---

## 📊 API Endpoints

| Method | Endpoint    | Description                        |
|--------|-------------|------------------------------------|
| POST   | `/analyze`  | Analyze + optimize a SQL query     |
| POST   | `/compare`  | Compare original vs optimized      |
| GET    | `/history`  | Fetch audit log                    |
| POST   | `/report`   | Generate PDF report                |
| GET    | `/`         | Health check                       |

Full Swagger docs: `http://localhost:8000/docs`

---

## 🧠 Query Issues Detected

| Code | Severity | Description |
|------|----------|-------------|
| SELECT_STAR | Critical | SELECT * — fetch only needed columns |
| NO_WHERE | Critical | Full table scan — missing WHERE |
| NO_LIMIT | Warning | Unbounded result set |
| NESTED_SUBQUERY | Critical | N+1 correlated subquery |
| FUNCTION_ON_COLUMN | Critical | YEAR()/MONTH() kills index |
| LEADING_WILDCARD | Warning | LIKE '%val' disables index |
| CARTESIAN_JOIN | Critical | Missing JOIN condition |
| ORDER_BY_CHECK | Info | Verify ORDER BY column is indexed |
| OR_CONDITION | Warning | OR may prevent index use |

---

## 🛡️ Production Safety Checks

1. Write operation guard (no DELETE/DROP/UPDATE)
2. Base table coverage
3. JOIN completeness
4. WHERE clause preservation
5. NULL handling
6. LIMIT/pagination
7. Locking impact
8. Aggregate preservation

---

## 📄 PDF Report Sections

1. Overview (score, safety, metrics)
2. Original Query
3. Issues Identified
4. Optimized Query
5. Optimization Suggestions
6. Performance Comparison (before/after table)
7. Execution Plan Summary
8. Safety Validation Checklist

---

## 🧪 Sample Slow Queries

See `database/sample_data.sql` for 5 test queries covering:
- SELECT * across 3 tables
- Correlated subquery (N+1)
- Function on indexed column
- Cartesian JOIN
- Well-optimized query (baseline)
