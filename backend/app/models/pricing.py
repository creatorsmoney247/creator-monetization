from pydantic import BaseModel

class PricingRequest(BaseModel):
    followers: int
    avg_views: int
    engagement_rate: float


class PricingResponse(BaseModel):
    recommended_price: int
    minimum_price: int
    tier: str
