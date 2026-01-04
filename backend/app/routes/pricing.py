# backend/app/routes/pricing.py

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.pricing_engine import calculate_pricing

router = APIRouter(prefix="/pricing", tags=["Pricing"])


class PricingRequest(BaseModel):
    followers: int
    avg_views: int
    engagement_rate: float


@router.post("/calculate")
def calculate_price(data: PricingRequest):
    return calculate_pricing(
        followers=data.followers,
        avg_views=data.avg_views,
        engagement_rate=data.engagement_rate
    )
