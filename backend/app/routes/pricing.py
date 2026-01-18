# backend/app/routes/pricing.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.pro_service import is_user_pro
from app.services.hybrid_pricing_engine import hybrid_pricing_engine


router = APIRouter(prefix="/pricing", tags=["Pricing"])


class PricingPayload(BaseModel):
    telegram_id: str
    followers: Optional[int] = None
    avg_views: Optional[int] = None
    engagement_rate: Optional[float] = None
    platform: str
    niche: str


@router.post("/calculate")
def calculate_pricing(data: PricingPayload):
    """
    Unified Hybrid Pricing Endpoint
    - Supports followers-only
    - Supports views-only
    - Supports full stats
    """

    # PLATFORM + NICHE REQUIRED
    if not data.platform or not data.niche:
        raise HTTPException(status_code=400, detail="platform and niche are required")

    # CHECK PRO STATUS FROM DB
    try:
        pro_user = is_user_pro(data.telegram_id)
    except Exception:
        pro_user = False

    # RUN HYBRID ENGINE
    result = hybrid_pricing_engine(
        followers=data.followers,
        avg_views=data.avg_views,
        engagement=data.engagement_rate,
        platform=data.platform,
        niche=data.niche,
        is_pro=pro_user
    )

    # HANDLE INSUFFICIENT DATA
    if result.get("error"):
        raise HTTPException(status_code=400, detail="insufficient_data")

    # RETURN STRUCTURED JSON
    return result
