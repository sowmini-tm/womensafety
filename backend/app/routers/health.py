from fastapi import APIRouter

from ..database import check_database_connection

router = APIRouter()


@router.get("/health", tags=["Health"])
def health_check():
    db_reachable, db_error = check_database_connection()
    return {
        "success": True,
        "data": {
            "status": "ok",
            "database": {
                "reachable": db_reachable,
                "error": db_error,
            },
        },
        "message": "Backend is healthy.",
    }
