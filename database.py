from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

# Create engine (SQLAlchemy Core — no ORM)
engine = create_engine(settings.DATABASE_URL or "sqlite:///:memory:")


def get_connection():
    """Get a raw database connection."""
    return engine.connect()


def execute_query(sql: str) -> list[dict]:
    """
    Execute a raw SQL query and return results as a list of dicts.
    Returns an empty list for a local demo or empty database.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = result.keys()
            rows = result.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    except Exception:
        return []


def get_schema_info() -> str:
    """
    Introspect the database and return a schema description string
    for use in the LLM prompt.
    """
    try:
        inspector = inspect(engine)
        schema_parts = []

        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            col_descriptions = ", ".join(
                f"{col['name']} ({col['type']})" for col in columns
            )
            schema_parts.append(f"Table: {table_name}\n  Columns: {col_descriptions}")

        return "\n\n".join(schema_parts)
    except Exception:
        return "Table: patients\n  Columns: id (INTEGER), first_name (TEXT), last_name (TEXT), gender (TEXT), date_of_birth (TEXT)\n\nTable: diagnoses\n  Columns: id (INTEGER), patient_id (INTEGER), diagnosis_name (TEXT), diagnosed_at (TEXT)\n\nTable: admissions\n  Columns: id (INTEGER), patient_id (INTEGER), ward (TEXT), reason (TEXT), admitted_at (TEXT), discharged_at (TEXT)\n\nTable: medications\n  Columns: id (INTEGER), patient_id (INTEGER), medication_name (TEXT), dosage (TEXT), frequency (TEXT), active (BOOLEAN)"
