def calculate_price(followers: int, avg_views: int, engagement_rate: float):
    base_cpm = 1500  # ₦ per 1k views (Nigeria market)

    engagement_multiplier = 1 + (engagement_rate * 5)
    reach_score = avg_views / max(followers, 1)

    raw_price = (avg_views / 1000) * base_cpm
    adjusted_price = raw_price * engagement_multiplier * (1 + reach_score)

    recommended = round(adjusted_price / 1000) * 1000
    minimum = int(recommended * 0.7)

    # Tier logic
    if followers < 10000:
        tier = "Free"
    elif followers < 100000:
        tier = "Pro"
    else:
        tier = "Elite"

    return {
        "recommended_price": recommended,
        "minimum_price": minimum,
        "tier": tier
    }
