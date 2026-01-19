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
    Legacy endpoint — returns single pricing values for backwards compatibility.
    """

    if not data.platform or not data.niche:
        raise HTTPException(status_code=400, detail="platform and niche are required")

    try:
        pro_user = is_user_pro(data.telegram_id)
    except Exception:
        pro_user = False

    result = hybrid_pricing_engine(
        followers=data.followers,
        avg_views=data.avg_views,
        engagement=data.engagement_rate,
        platform=data.platform,
        niche=data.niche,
        is_pro=pro_user,
        mode="single"
    )

    if result.get("error"):
        raise HTTPException(status_code=400, detail="insufficient_data")

    return result


@router.post("/range")
def calculate_pricing_range(data: PricingPayload):
    """
    New endpoint — returns MIN–MID–MAX pricing for Telegram bot.
    """

    if not data.platform or not data.niche:
        raise HTTPException(status_code=400, detail="platform and niche are required")

    try:
        pro_user = is_user_pro(data.telegram_id)
    except Exception:
        pro_user = False

    result = hybrid_pricing_engine(
        followers=data.followers,
        avg_views=data.avg_views,
        engagement=data.engagement_rate,
        platform=data.platform,
        niche=data.niche,
        is_pro=pro_user,
        mode="range"  # <---- critical
    )

    if result.get("error"):
        return result

    return result
