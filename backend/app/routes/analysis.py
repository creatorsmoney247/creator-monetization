from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_analysis():
    return {"message": "Analysis endpoint working!"}
