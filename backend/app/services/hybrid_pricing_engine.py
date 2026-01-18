# backend/app/services/hybrid_pricing_engine.py

from typing import Optional, Dict, Any


# ---------------------------------------------
# GLOBAL CPM RANGES (USD) — Mixed/Auto Mode
# midpoints will be used for pricing
# ---------------------------------------------
PLATFORM_CPM_USD = {
    "instagram":  (12, 30),   # high value platform
    "tiktok":     (8, 18),    # mid-range CPM
    "youtube":    (15, 40),   # premium CPM
    "twitter":    (4, 10),    # lower CPM historically
    "facebook":   (6, 14),    # dependable mid-range CPM
}

# ---------------------------------------------
# NICHE MULTIPLIERS — Interest/Conversion strength
# ---------------------------------------------
NICHE_MULT = {
    "tech":        2.5,
    "business":    2.3,
    "finance":     2.8,
    "beauty":      2.0,
    "gaming":      1.8,
    "fitness":     1.6,
    "lifestyle":   1.4,
    "comedy":      1.2,
    "education":   1.5,
    "general":     1.0,
}

# ---------------------------------------------
# FOLLOWER FLOOR PRICING (NGN)
# ---------------------------------------------
FLOOR_NGN_PER_10K = 100_000  # 100K NGN per 10K followers

# ---------------------------------------------
# AFRICA MARKET DISCOUNT (Mixed/Auto)
# ---------------------------------------------
AFRICA_DISCOUNT = 0.45  # ~45% lower advertiser CPM budgets

# ---------------------------------------------
# USAGE MULTIPLIERS (PRO unlocks controls)
# ---------------------------------------------
USAGE_MULT = {
    3: 2.0,   # 3 months
    6: 3.0,   # 6 months
    12: 4.0   # 12 months
}

# ---------------------------------------------
# WHITELISTING MULTIPLIER (PRO only)
# ---------------------------------------------
WHITELIST_MULT = 2.0

# ---------------------------------------------
# FX RATE (Static for now)
# ---------------------------------------------
USD_TO_NGN = 1300


def hybrid_pricing_engine(
    followers: Optional[int],
    avg_views: Optional[int],
    engagement: Optional[float],
    platform: str,
    niche: str,
    is_pro: bool
) -> Dict[str, Any]:
    """
    Hybrid Pricing Engine (Mixed/Auto model)

    Supports:
    - Full stats (followers + views + engagement)
    - Followers-only
    - Views-only
    """

    platform = (platform or "").lower()
    niche = (niche or "").lower()

    # CPM midpoint
    if platform in PLATFORM_CPM_USD:
        low, high = PLATFORM_CPM_USD[platform]
        cpm_usd = (low + high) / 2.0
    else:
        cpm_usd = 10  # sensible fallback

    # Apply Africa discount since bot is currently NGN-facing
    cpm_usd_africa = cpm_usd * AFRICA_DISCOUNT

    # Niche multiplier
    niche_mult = NICHE_MULT.get(niche, 1.0)

    # Followers floor price (NGN)
    floor_ngn = 0
    if followers:
        floor_ngn = (followers / 10_000) * FLOOR_NGN_PER_10K

    # Views valuation (USD → NGN) with niche multiplier
    views_ngn = 0
    if avg_views:
        base_usd = (avg_views / 1000) * cpm_usd_africa  # USD
        niche_usd = base_usd * niche_mult               # USD
        views_ngn = niche_usd * USD_TO_NGN              # NGN

    # Determine mode
    if followers and avg_views and engagement:
        mode = "full"  # full hybrid mode
        base_value_ngn = max(views_ngn, floor_ngn)

    elif followers and not avg_views:
        mode = "followers_only"
        base_value_ngn = floor_ngn

    elif avg_views and not followers:
        mode = "views_only"
        base_value_ngn = views_ngn

    else:
        mode = "unknown"
        return {
            "error": "insufficient_data",
            "mode": mode
        }

    # Apply default usage rights (3 months for FREE)
    usage_months = 3
    usage_mult = USAGE_MULT.get(usage_months, 2.0)
    ngn_with_usage = base_value_ngn * usage_mult

    # PRO whitelisting
    if is_pro:
        ngn_whitelist = ngn_with_usage * WHITELIST_MULT
    else:
        ngn_whitelist = None

    # Convert to USD for PRO users only (Dual display)
    usd_recommended = ngn_with_usage / USD_TO_NGN
    usd_whitelist = None
    if is_pro and ngn_whitelist:
        usd_whitelist = ngn_whitelist / USD_TO_NGN

    # Minimum acceptable = 50% of recommended floor
    ngn_minimum = ngn_with_usage * 0.5

    return {
        "mode": mode,
        "platform": platform,
        "niche": niche,
        "followers": followers,
        "avg_views": avg_views,
        "engagement": engagement,
        "base_value_ngn": int(base_value_ngn),
        "recommended_ngn": int(ngn_with_usage),
        "minimum_ngn": int(ngn_minimum),
        "recommended_usd": round(usd_recommended, 2),
        "whitelist_ngn": int(ngn_whitelist) if ngn_whitelist else None,
        "whitelist_usd": round(usd_whitelist, 2) if usd_whitelist else None,
        "usage_months": usage_months,
        "is_pro": is_pro
    }
