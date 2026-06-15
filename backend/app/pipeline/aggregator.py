def build_report(vision, clusters, playstyle, lstm, game_title):
    k = vision.get("kills", 0)
    d = vision.get("deaths", 0)
    kd = round(k / max(1, d), 2)
    hs = vision.get("headshot_pct", 0)
    accuracy = min(100, round(hs * 0.55 + min(kd / 4, 1.0) * 45))
    rating = min(100, max(0, round(kd * 18 + hs * 0.4 + k * 0.6 - d * 0.4)))

    return {
        "game": vision.get("game", game_title),
        "map_name": vision.get("map_name", "Unknown"),
        "kills": k, "deaths": d,
        "assists": vision.get("assists", 0),
        "kd_ratio": kd,
        "headshot_percentage": hs,
        "accuracy": accuracy,
        "performance_rating": rating,
        "weapon_usage": vision.get("weapon_stats", {}),
        "most_used_weapon": vision.get("most_used_weapon", "Unknown"),
        "multi_kills": vision.get("multi_kills", {"2k": 0, "3k": 0, "4k+": 0}),
        "playstyle": playstyle["label"],
        "playstyle_confidence": playstyle["confidence"],
        "predicted_kd": lstm["predicted_kd"],
        "heatmap_points": clusters["heatmap_points"],
        "timeline": vision.get("timeline", []),
        "kill_events": vision.get("kill_events", []),
        "data_source": vision.get("data_source", "kill feed analysis"),
        "confidence": vision.get("confidence", "MEDIUM"),
        "total_kills": k,
        "total_deaths": d,
    }
