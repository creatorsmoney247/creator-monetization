from typing import Optional, Dict, Any

# ---------------------------------------------
# GLOBAL CPM RANGES (USD) — Midpoints used
# ---------------------------------------------
PLATFORM_CPM_USD = {
    "instagram":  (12, 30),   # high value platform
    "tiktok":     (4, 10),    # lower CPM
    "youtube":    (18, 45),   # premium CPM
    "twitter":    (2, 6),     # very low CPM historically (X)
    "facebook":   (6, 14),    # dependable mid-range CPM
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
FLOOR_NGN_PER_10K = 120_000  # updated to modern Nigeria creator rates

# ---------------------------------------------
# PLATFORM FLOOR MULTIPLIERS (Differentiation)
# ---------------------------------------------
FLOOR_PLATFORM_MULT = {
    "instagram": 1.0,
    "tiktok":    0.75,
    "youtube":   1.35,   # YouTube commands stronger brand budgets
    "twitter":   0.50,
    "facebook":  0.65,
}

# ---------------------------------------------
# AFRICA MARKET DISCOUNT (CPM normalizing)
# ---------------------------------------------
AFRICA_DISCOUNT = 0.55  # Africa CPM ~45–60% lower than US/EU

# ---------------------------------------------
# USAGE MULTIPLIERS (PRO unlocks control)
# ---------------------------------------------
USAGE_MULT = {
    3: 2.0,   # 3 months
    6: 3.0,   # 6 months
    12: 4.0   # 12 months
}

# ---------------------------------------------
# WHITELISTING MULTIPLIER (PRO only)
# ---------------------------------------------
WHITELIST_MULT = 2.2

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

    platform = (platform or "").lower()
    niche = (niche or "").lower()

    # ---- 1. CPM Midpoint ----
    if platform in PLATFORM_CPM_USD:
        low, high = PLATFORM_CPM_USD[platform]
        cpm_usd = (low + high) / 2.0   # midpoint
    else:
        cpm_usd = 10  # fallback

    # Apply Africa CPM normalization
    cpm_usd_local = cpm_usd * AFRICA_DISCOUNT

    # ---- 2. Niche Multiplier ----
    niche_mult = NICHE_MULT.get(niche, 1.0)

    # ---- 3. Followers Floor (NGN) ----
    floor_ngn = 0
    if followers:
        base_floor = (followers / 10_000) * FLOOR_NGN_PER_10K
        floor_mult = FLOOR_PLATFORM_MULT.get(platform, 1.0)
        floor_ngn = base_floor * floor_mult

    # ---- 4. Views Valuation (USD → NGN) ----
    views_ngn = 0
    if avg_views:
        base_usd = (avg_views / 1000) * cpm_usd_local
        niche_usd = base_usd * niche_mult
        views_ngn = niche_usd * USD_TO_NGN

    # ---- 5. Hybrid Mode ----
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

    # ---- 6. Usage Rights (Default 3 months) ----
    usage_months = 3
    usage_mult = USAGE_MULT.get(usage_months, 2.0)
    ngn_with_usage = base_value_ngn * usage_mult

    # ---- 7. PRO Whitelisting ----
    if is_pro:
        ngn_whitelist = ngn_with_usage * WHITELIST_MULT
    else:
        ngn_whitelist = None

    # ---- 8. USD Dual Display ----
    usd_recommended = ngn_with_usage / USD_TO_NGN
    usd_whitelist = (ngn_whitelist / USD_TO_NGN) if (is_pro and ngn_whitelist) else None

    # ---- 9. Minimum Acceptable ----
    ngn_minimum = ngn_with_usage * 0.50

    # ---- 10. Response ----
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
