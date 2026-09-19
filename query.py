from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.nlq_service import natural_language_to_sql

router = APIRouter()


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    generated_sql: str
    results: list[dict]
    row_count: int


@router.post("/query", response_model=QueryResponse)
async def query_emr(request: QueryRequest):
    """
    Convert a natural language question into SQL and return results
    from the EMR database.

    Example:
    {
        "question": "Show me all diabetic patients admitted last week"
    }
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = await natural_language_to_sql(request.question)
        return result
    except ValueError as e:
        # SQL validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/health")
def health_check():
    """Check if the service is running."""
    return {"status": "healthy", "service": "EMR NLQ Interface"}
