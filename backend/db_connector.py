import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def get_connection(db_type: str = "postgresql"):
    """Return a SQLAlchemy engine for the specified database type."""
    if db_type == "postgresql":
        url = os.getenv("POSTGRES_URL", "postgresql://user:pass@localhost:5432/querylens")
    elif db_type == "mysql":
        url = os.getenv("MYSQL_URL", "mysql+pymysql://user:pass@localhost:3306/ecommerce")
    else:
        url = "sqlite:///./querylens_history.db"

    try:
        engine = create_engine(url, pool_pre_ping=True)
        return engine
    except Exception as e:
        raise ConnectionError(f"Could not connect to {db_type}: {str(e)}")


def run_explain(query: str, db_type: str) -> list:
    """Run EXPLAIN / EXPLAIN ANALYZE and return parsed plan lines."""
    engine = get_connection(db_type)
    plan_lines = []

    try:
        with engine.connect() as conn:
            if db_type == "postgresql":
                result = conn.execute(text(f"EXPLAIN ANALYZE {query}"))
            else:
                result = conn.execute(text(f"EXPLAIN {query}"))

            for row in result:
                plan_lines.append(str(row[0]))
    except SQLAlchemyError as e:
        plan_lines = [f"Could not fetch execution plan: {str(e)}"]

    return plan_lines


def test_connections() -> dict:
    """Test all configured database connections."""
    results = {}
    for db_type in ["postgresql", "mysql"]:
        try:
            engine = get_connection(db_type)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            results[db_type] = {"status": "connected", "error": None}
        except Exception as e:
            results[db_type] = {"status": "failed", "error": str(e)}
    return results
