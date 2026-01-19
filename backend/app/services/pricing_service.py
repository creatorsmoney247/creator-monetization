def calculate_price(followers: int, avg_views: int, engagement_rate: float):
    """
    Local Nigeria CPM model with engagement weighting + reach score.
    Now returns MIN, MID, MAX ranges + original fields for backward compatibility.
    """

    base_cpm = 1500  # ₦ per 1k views (Nigeria market baseline)

    # Engagement & reach weighting
    engagement_multiplier = 1 + (engagement_rate * 5)
    reach_score = avg_views / max(followers, 1)

    # Base raw value
    raw_price = (avg_views / 1000) * base_cpm
    adjusted_price = raw_price * engagement_multiplier * (1 + reach_score)

    # Original recommended logic
    recommended = round(adjusted_price / 1000) * 1000
    minimum = int(recommended * 0.7)

    # --- NEW RANGE LOGIC ---
    # MIN ~70% (same as legacy)
    price_min = minimum

    # MID = recommended
    price_mid = recommended

    # MAX = recommended * 2 (premium brand/usage scenario)
    price_max = int(recommended * 2)

    # Tier logic remains unchanged
    if followers < 10000:
        tier = "Free"
    elif followers < 100000:
        tier = "Pro"
    else:
        tier = "Elite"

    return {
        # Legacy fields (no breakage)
        "recommended_price": recommended,
        "minimum_price": minimum,
        "tier": tier,

        # New Range fields
        "min": price_min,
        "mid": price_mid,
        "max": price_max,

        # Helpful datapoints for Telegram output
        "followers": followers,
        "avg_views": avg_views,
        "engagement_rate": engagement_rate,
        "currency": "NGN",
        "usage_rights": "3-month",
        "whitelisting": False
    }
