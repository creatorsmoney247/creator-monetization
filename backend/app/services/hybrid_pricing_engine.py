from typing import Optional, Dict, Any

# ---------------------------------------------
# GLOBAL CPM RANGES (USD) — Midpoints used
# ---------------------------------------------
PLATFORM_CPM_USD = {
    "instagram":  (12, 30),
    "tiktok":     (4, 10),
    "youtube":    (18, 45),
    "twitter":    (2, 6),
    "facebook":   (6, 14),
}

# ---------------------------------------------
# PLATFORM FLOOR MULTIPLIERS
# ---------------------------------------------
FLOOR_PLATFORM_MULT = {
    "instagram": 1.0,
    "tiktok":    0.75,
    "youtube":   1.35,
    "twitter":   0.50,
    "facebook":  0.65,
    "other":     1.0,
}

# ---------------------------------------------
# NICHE MULTIPLIERS — Conversion Strength
# ---------------------------------------------
NICHE_MULT = {
    "tech":        2.4,
    "business":    2.2,
    "finance":     3.0,
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
FLOOR_NGN_PER_10K = 120_000

# ---------------------------------------------
# AFRICA MARKET DISCOUNT
# ---------------------------------------------
AFRICA_DISCOUNT = 0.55

# ---------------------------------------------
# USAGE MULTIPLIERS
# ---------------------------------------------
USAGE_MULT = {
    3: 2.0,
    6: 3.0,
    12: 4.0,
}

# ---------------------------------------------
# WHITELISTING MULTIPLIER (PRO only)
# ---------------------------------------------
WHITELIST_MULT = 2.2

# ---------------------------------------------
# PLATFORM SPREAD (for ranges)
# ---------------------------------------------
PLATFORM_SPREAD = {
    "youtube":   0.35,
    "instagram": 0.30,
    "tiktok":    0.25,
    "facebook":  0.25,
    "twitter":   0.25,
    "other":     0.25,
}

# ---------------------------------------------
# FX RATE
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

    platform = (platform or "").lower()
    niche = (niche or "").lower()

    # ---- CPM Midpoint ----
    if platform in PLATFORM_CPM_USD:
        low, high = PLATFORM_CPM_USD[platform]
        cpm_usd = (low + high) / 2.0
    else:
        cpm_usd = 10

    cpm_usd_local = cpm_usd * AFRICA_DISCOUNT

    # ---- Niche Multiplier ----
    niche_mult = NICHE_MULT.get(niche, 1.0)

    # ---- Followers Floor ----
    floor_ngn = 0
    if followers:
        base_floor = (followers / 10_000) * FLOOR_NGN_PER_10K
        floor_mult = FLOOR_PLATFORM_MULT.get(platform, 1.0)
        floor_ngn = base_floor * floor_mult

    # ---- Views Valuation ----
    views_ngn = 0
    if avg_views:
        base_usd = (avg_views / 1000) * cpm_usd_local
        views_ngn = (base_usd * niche_mult) * USD_TO_NGN

    # ---- Hybrid Mode ----
    if followers and avg_views and engagement:
        mode = "full"
        base_value_ngn = max(views_ngn, floor_ngn)
    elif followers and not avg_views:
        mode = "followers_only"
        base_value_ngn = floor_ngn
    elif avg_views and not followers:
        mode = "views_only"
        base_value_ngn = views_ngn
    else:
        return {"error": "insufficient_data", "mode": "unknown"}

    # ---- Usage Rights Default ----
    usage_months = 3
    usage_mult = USAGE_MULT.get(usage_months, 2.0)
    ngn_usage = base_value_ngn * usage_mult

    # ---- Range Spread ----
    spread = PLATFORM_SPREAD.get(platform, 0.25)
    range_low_ngn = ngn_usage * (1 - spread)
    range_high_ngn = ngn_usage * (1 + spread)

    # ---- Floor (Minimum Acceptable) ----
    floor_rate_ngn = ngn_usage * 0.50  # legal-safe definition

    # ---- PRO Whitelisting ----
    if is_pro:
        whitelist_ngn = ngn_usage * WHITELIST_MULT
        usd_whitelist = whitelist_ngn / USD_TO_NGN
    else:
        whitelist_ngn = None
        usd_whitelist = None

    # ---- USD Dual Display for PRO ----
    usd_recommended = ngn_usage / USD_TO_NGN

    return {
        "mode": mode,
        "platform": platform,
        "niche": niche,
        "followers": followers,
        "avg_views": avg_views,
        "engagement": engagement,
        "usage_months": usage_months,
        "range_low_ngn": int(range_low_ngn),
        "range_high_ngn": int(range_high_ngn),
        "floor_ngn": int(floor_rate_ngn),
        "recommended_usd": round(usd_recommended, 2),
        "whitelist_ngn": int(whitelist_ngn) if whitelist_ngn else None,
        "whitelist_usd": round(usd_whitelist, 2) if usd_whitelist else None,
        "is_pro": is_pro
    }
