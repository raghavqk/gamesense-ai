import numpy as np
from sklearn.cluster import DBSCAN


def run_dbscan(positions: list) -> dict:
    if len(positions) < 5:
        return {"num_clusters": 1, "clusters": [], "heatmap_points": [{"x": 0.5, "y": 0.5, "intensity": 1.0}]}

    arr = np.array(positions, dtype=float)
    if arr.std() < 1e-5:
        return {"num_clusters": 1, "clusters": [], "heatmap_points": [{"x": 0.5, "y": 0.5, "intensity": 1.0}]}

    db = DBSCAN(eps=0.06, min_samples=3).fit(arr)
    labels = db.labels_

    clusters = []
    for lbl in set(labels) - {-1}:
        mask = labels == lbl
        pts = arr[mask]
        c = pts.mean(axis=0)
        clusters.append({
            "cluster_id": int(lbl),
            "count": int(mask.sum()),
            "cx": float(c[0]),
            "cy": float(c[1]),
        })

    clusters.sort(key=lambda c: c["count"], reverse=True)
    top = clusters[0]["count"] if clusters else 1
    heatmap = [
        {"x": c["cx"], "y": c["cy"], "intensity": round(c["count"] / top, 2)}
        for c in clusters[:8]
    ]

    return {"num_clusters": len(clusters), "heatmap_points": heatmap}
