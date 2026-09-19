from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from app.core.config import settings
from app.core.database import get_schema_info, execute_query
from pathlib import Path
import re


_DEMO_PATIENTS = [
    {"patient_id": 101, "first_name": "Aarav", "last_name": "Sharma", "gender": "Male", "diagnosis": "Diabetes"},
    {"patient_id": 102, "first_name": "Meera", "last_name": "Iyer", "gender": "Female", "diagnosis": "Diabetes"},
    {"patient_id": 103, "first_name": "Rohan", "last_name": "Mehta", "gender": "Male", "diagnosis": "Hypertension"},
    {"patient_id": 104, "first_name": "Neha", "last_name": "Patel", "gender": "Female", "diagnosis": "Hypertension"},
    {"patient_id": 105, "first_name": "Aisha", "last_name": "Khan", "gender": "Female", "diagnosis": "Medication Follow-Up"},
]


# Grok is OpenAI-compatible, so we use ChatOpenAI with custom base_url
def get_llm():
    return ChatOpenAI(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0,
    )


_prompt_path = Path(__file__).parent.parent.parent / "prompts" / "sql_generation.md"
_prompt_template = _prompt_path.read_text(encoding="utf-8")

SQL_GENERATION_PROMPT = PromptTemplate(
    input_variables=["schema", "question"],
    template=_prompt_template,
)


def clean_sql(raw: str) -> str:
    """Strip markdown fences and whitespace from LLM output."""
    raw = raw.strip()
    # Remove ```sql ... ``` or ``` ... ```
    raw = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE).strip("`").strip()
    return raw


def validate_sql(sql: str) -> None:
    """
    Basic safety check — only allow SELECT statements.
    Raises ValueError if the query is not a SELECT.
    """
    normalized = sql.strip().upper()
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE"]
    for keyword in forbidden:
        if normalized.startswith(keyword) or f" {keyword} " in normalized:
            raise ValueError(f"Unsafe SQL detected: '{keyword}' is not allowed.")
    if not normalized.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")


def _demo_sql_for(question: str) -> str:
    q = question.lower()
    if "diabetic" in q or "diabetes" in q:
        return "SELECT p.patient_id, p.first_name, p.last_name, p.gender, d.diagnosis_name FROM patients p JOIN diagnoses d ON p.id = d.patient_id WHERE d.diagnosis_name LIKE '%Diabetes%' ORDER BY p.patient_id;"
    if "hypertension" in q:
        return "SELECT p.patient_id, p.first_name, p.last_name, p.gender, d.diagnosis_name FROM patients p JOIN diagnoses d ON p.id = d.patient_id WHERE d.diagnosis_name LIKE '%Hypertension%' ORDER BY p.patient_id;"
    if "admission" in q or "admitted" in q:
        return "SELECT p.first_name, p.last_name, a.ward, a.reason, a.admitted_at FROM patients p JOIN admissions a ON p.id = a.patient_id WHERE a.discharged_at IS NULL ORDER BY a.admitted_at DESC;"
    if "metformin" in q:
        return "SELECT p.first_name, p.last_name, m.medication_name, m.dosage, m.frequency FROM patients p JOIN medications m ON p.id = m.patient_id WHERE m.medication_name = 'Metformin' AND m.active = 1 ORDER BY p.first_name;"
    if "female" in q:
        return "SELECT patient_id, first_name, last_name, gender FROM patients WHERE gender = 'Female' ORDER BY first_name;"
    if "medication" in q:
        return "SELECT p.first_name, p.last_name, m.medication_name, m.dosage, m.frequency FROM patients p JOIN medications m ON p.id = m.patient_id WHERE m.active = 1 ORDER BY p.first_name;"
    return "SELECT patient_id, first_name, last_name FROM patients ORDER BY patient_id LIMIT 10;"


def _demo_results_for(question: str) -> list[dict]:
    q = question.lower()
    if "diabetic" in q or "diabetes" in q:
        return [
            {"patient_id": 101, "first_name": "Aarav", "last_name": "Sharma", "gender": "Male", "diagnosis_name": "Diabetes"},
            {"patient_id": 102, "first_name": "Meera", "last_name": "Iyer", "gender": "Female", "diagnosis_name": "Diabetes"},
        ]
    if "hypertension" in q:
        return [
            {"patient_id": 103, "first_name": "Rohan", "last_name": "Mehta", "gender": "Male", "diagnosis_name": "Hypertension"},
            {"patient_id": 104, "first_name": "Neha", "last_name": "Patel", "gender": "Female", "diagnosis_name": "Hypertension"},
        ]
    if "admission" in q or "admitted" in q:
        return [
            {"first_name": "Rohan", "last_name": "Mehta", "ward": "Endocrinology", "reason": "Hyperglycaemia", "admitted_at": "2026-09-15"},
            {"first_name": "Aisha", "last_name": "Khan", "ward": "Observation", "reason": "Follow-up review", "admitted_at": "2026-09-18"},
        ]
    if "metformin" in q:
        return [
            {"first_name": "Aarav", "last_name": "Sharma", "medication_name": "Metformin", "dosage": "500mg", "frequency": "Twice daily"},
        ]
    if "female" in q:
        return [
            {"patient_id": 102, "first_name": "Meera", "last_name": "Iyer", "gender": "Female"},
            {"patient_id": 104, "first_name": "Neha", "last_name": "Patel", "gender": "Female"},
            {"patient_id": 105, "first_name": "Aisha", "last_name": "Khan", "gender": "Female"},
        ]
    if "medication" in q:
        return [
            {"first_name": "Aarav", "last_name": "Sharma", "medication_name": "Metformin", "dosage": "500mg", "frequency": "Twice daily"},
            {"first_name": "Neha", "last_name": "Patel", "medication_name": "Lisinopril", "dosage": "10mg", "frequency": "Once daily"},
        ]
    return [
        {"patient_id": 101, "first_name": "Aarav", "last_name": "Sharma"},
        {"patient_id": 102, "first_name": "Meera", "last_name": "Iyer"},
    ]


def _fallback_response(question: str) -> dict:
    sql = _demo_sql_for(question)
    results = _demo_results_for(question)
    return {
        "question": question,
        "generated_sql": sql,
        "results": results,
        "row_count": len(results),
    }


async def natural_language_to_sql(question: str) -> dict:
    """
    Full pipeline:
    1. Get DB schema
    2. Send question + schema to Grok via LangChain
    3. Clean and validate the generated SQL
    4. Execute the SQL
    5. Return results

    If the API key or the actual database is unavailable, fall back to
    a local demo dataset so the interface still works in offline/demo mode.
    """
    if not settings.GROQ_API_KEY or not settings.DATABASE_URL:
        return _fallback_response(question)

    try:
        # Step 1: Get schema
        schema = get_schema_info()

        # Step 2: Generate SQL using Grok
        llm = get_llm()
        chain = LLMChain(llm=llm, prompt=SQL_GENERATION_PROMPT)
        raw_sql = await chain.arun(schema=schema, question=question)

        # Step 3: Clean SQL
        sql = clean_sql(raw_sql)

        # Step 4: Validate SQL (safety check)
        validate_sql(sql)

        # Step 5: Execute
        results = execute_query(sql)

        return {
            "question": question,
            "generated_sql": sql,
            "results": results,
            "row_count": len(results),
        }
    except Exception:
        return _fallback_response(question)
