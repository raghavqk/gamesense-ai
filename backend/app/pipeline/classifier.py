def classify_playstyle(vision: dict, clusters: dict) -> dict:
    k = vision.get("kills", 0)
    d = vision.get("deaths", 1)
    hs = vision.get("headshot_pct", 0)
    kd = k / max(1, d)
    nc = clusters.get("num_clusters", 1)

    if kd >= 3.5 and hs >= 50:
        label = "Aggressive Fragger"
        conf = {"Aggressive Fragger": 0.82, "Entry Fragger": 0.10, "Rifler": 0.04, "Passive Lurker": 0.02, "Support": 0.02}
    elif kd >= 2.0 and k >= 12:
        label = "Entry Fragger"
        conf = {"Aggressive Fragger": 0.12, "Entry Fragger": 0.74, "Rifler": 0.07, "Passive Lurker": 0.04, "Support": 0.03}
    elif hs >= 55 and kd >= 1.5:
        label = "Rifler / Duelist"
        conf = {"Aggressive Fragger": 0.08, "Entry Fragger": 0.12, "Rifler": 0.72, "Passive Lurker": 0.04, "Support": 0.04}
    elif kd < 0.9:
        label = "Passive Lurker"
        conf = {"Aggressive Fragger": 0.03, "Entry Fragger": 0.05, "Rifler": 0.08, "Passive Lurker": 0.76, "Support": 0.08}
    elif nc >= 5:
        label = "Roamer / Support"
        conf = {"Aggressive Fragger": 0.05, "Entry Fragger": 0.08, "Rifler": 0.12, "Passive Lurker": 0.10, "Support": 0.65}
    else:
        label = "Defensive Anchor"
        conf = {"Aggressive Fragger": 0.05, "Entry Fragger": 0.10, "Rifler": 0.20, "Passive Lurker": 0.15, "Defensive Anchor": 0.50}

    return {"label": label, "confidence": conf}
