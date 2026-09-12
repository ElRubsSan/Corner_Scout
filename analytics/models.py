"""Pre-match features and strictly temporal model evaluation."""
import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss, precision_recall_fscore_support, silhouette_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from analytics.io import ROOT, data_dir, digest, now, write_json

FEATURES = ["historical_scr", "corners_per_match", "short_share", "high_share"]


def history_features(history: pd.DataFrame, n_matches: int) -> dict:
    valid = history[history.valid_sequence]
    return {"historical_scr": float(valid.shot_within_15s.mean()) if len(valid) else 0.0,
            "corners_per_match": len(history) / n_matches if n_matches else 0.0,
            "short_share": float((history.delivery == "corto").mean()) if len(history) else 0.0,
            "high_share": float((history.height == "High Pass").mean()) if len(history) else 0.0}


def previous_matches(matches: pd.DataFrame, team: str, cutoff: str) -> pd.DataFrame:
    return matches[((matches.home_team == team) | (matches.away_team == team)) & (matches.match_date < cutoff)].sort_values(["match_date", "kick_off", "match_id"], ascending=False).head(8)


def features(matches: pd.DataFrame, corners: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for match in matches.itertuples():
        for team in (match.home_team, match.away_team):
            window = previous_matches(matches, team, match.match_date)
            if len(window) != 8:
                continue
            history = corners[(corners.team == team) & corners.match_id.isin(window.match_id)]
            values = history_features(history, 8)
            targets = corners[(corners.team == team) & (corners.match_id == match.match_id) & corners.valid_sequence]
            for event in targets.itertuples():
                rows.append({"event_id": event.event_id, "match_id": match.match_id, "match_date": match.match_date, "history_max_date": str(window.match_date.max()), "team": team, "target": int(event.shot_within_15s), **values})
    return pd.DataFrame(rows)


def metrics(y, probabilities) -> dict:
    precision, recall, f1, _ = precision_recall_fscore_support(y, probabilities >= 0.5, average="binary", zero_division=0)
    fraction, mean = calibration_curve(y, probabilities, n_bins=8, strategy="uniform")
    return {"pr_auc_ap": float(average_precision_score(y, probabilities)), "roc_auc": float(roc_auc_score(y, probabilities)) if len(set(y)) > 1 else None,
            "brier": float(brier_score_loss(y, probabilities)), "precision": float(precision), "recall": float(recall), "f1": float(f1), "threshold": 0.5,
            "calibration": [{"predicted": float(p), "observed": float(f)} for p, f in zip(mean, fraction)], "n": len(y)}


def estimators():
    return {"logistic": make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000, random_state=42)),
            "random_forest": RandomForestClassifier(n_estimators=200, min_samples_leaf=30, max_depth=4, random_state=42, n_jobs=1)}


def train() -> dict:
    root = data_dir()
    quality = json.loads((root / "processed/quality.json").read_text(encoding="utf-8"))
    if not quality["passed"]:
        raise ValueError("Data audit must pass before modeling")
    corners = pd.read_parquet(root / "processed/corners.parquet")
    matches = pd.read_parquet(root / "processed/matches.parquet")
    frame = features(matches, corners)
    assert (frame.history_max_date < frame.match_date).all()
    frame.to_parquet(root / "processed/features.parquet", index=False)
    # Two expanding validation blocks; final block is untouched until selection.
    splits = [("2016-01-01", "2016-02-15"), ("2016-02-15", "2016-04-01"), ("2016-04-01", "2016-06-01")]
    evaluations = []
    artifact = Path(os.environ.get("CORNERSCOUT_ARTIFACTS_DIR", ROOT / "artifacts")) / "v0.3"
    artifact.mkdir(parents=True, exist_ok=True)
    for start, end in splits:
        training = frame[frame.match_date < start]
        testing = frame[(frame.match_date >= start) & (frame.match_date < end)]
        assert set(training.match_id).isdisjoint(set(testing.match_id))
        y = testing.target.to_numpy()
        result = {"start": start, "end_exclusive": end, "train_matches": sorted(training.match_id.unique().tolist()), "test_matches": sorted(testing.match_id.unique().tolist()), "baseline": metrics(y, np.full(len(y), training.target.mean()))}
        for label, estimator in estimators().items():
            estimator.fit(training[FEATURES], training.target)
            result[label] = metrics(y, estimator.predict_proba(testing[FEATURES])[:, 1])
            if start == splits[-1][0]:
                joblib.dump(estimator, artifact / f"{label}.joblib")
        evaluations.append(result)
    approved = [name for name in estimators() if all(e[name]["brier"] < e["baseline"]["brier"] and e[name]["pr_auc_ap"] > e["baseline"]["pr_auc_ap"] for e in evaluations[:2])]
    selected = min(approved, key=lambda n: sum(e[n]["brier"] for e in evaluations[:2])) if approved else "baseline"
    if selected != "baseline" and evaluations[-1][selected]["brier"] >= evaluations[-1]["baseline"]["brier"]:
        selected = "baseline"
    # KMeans snapshot per month: each fit uses strictly earlier matches.
    cluster_info = []
    assignments = []
    with threadpool_limits(limits=1):
        for cutoff in pd.date_range("2015-10-01", "2016-06-01", freq="MS").strftime("%Y-%m-%d"):
            history = corners[(corners.match_date < cutoff) & corners.spatial_valid]
            matrix = history[["end_x", "end_y"]].to_numpy()
            scaler = StandardScaler().fit(matrix)
            scaled = scaler.transform(matrix)
            candidates = []
            for k in range(2, 7):
                km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(scaled)
                sizes = np.bincount(km.labels_)
                candidates.append((silhouette_score(scaled, km.labels_, sample_size=min(1000, len(scaled)), random_state=42), km, sizes))
            allowed = [item for item in candidates if min(item[2]) >= 20]
            score, km, sizes = max(allowed or candidates, key=lambda item: item[0])
            payload = {"scaler": scaler, "kmeans": km, "available_from": cutoff}
            joblib.dump(payload, artifact / f"clusters-{cutoff}.joblib")
            cluster_info.append({"available_from": cutoff, "k": km.n_clusters, "silhouette": float(score), "sizes": sizes.tolist(), "centers": scaler.inverse_transform(km.cluster_centers_).tolist()})
            # Save IDs for every prior corner in this snapshot; backend needs no raw/model load.
            for event_id, label in zip(history.event_id, km.labels_):
                assignments.append({"available_from": cutoff, "event_id": event_id, "cluster": int(label)})
    pd.DataFrame(assignments).to_parquet(root / "processed/clusters.parquet", index=False)
    report = {"selected": selected, "available_from": "2016-06-01", "features": FEATURES, "evaluations": evaluations, "clusters": cluster_info,
              "source_manifest_sha256": quality["source_manifest_sha256"], "processed_at": now(), "artifact_version": "v0.3",
              "selection_rule": "Brier lower and AP higher in BOTH validation blocks; final holdout Brier must also improve. Otherwise serve historical baseline.",
              "limitations": ["Una temporada historica; no informacion actual.", "Variables de equipo compartidas por corners del mismo partido.", "Umbral 0.5 ilustrativo; priorizar calibracion sobre F1.", "K-Means usa destino del pase solo para descripcion, nunca como predictor."]}
    write_json(root / "processed/model-evaluation.json", report)
    write_json(ROOT / "docs/model-evaluation.json", report)
    write_json(artifact / "manifest.json", {p.name: digest(p) for p in artifact.glob("*.joblib")})
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1], "--", label="Ideal")
    for label in ["baseline", "logistic", "random_forest"]:
        points = evaluations[-1][label]["calibration"]
        ax.plot([p["predicted"] for p in points], [p["observed"] for p in points], marker="o", label=label)
    ax.set(xlabel="Probabilidad estimada", ylabel="Frecuencia observada", title="Calibracion: holdout temporal")
    ax.legend()
    fig.savefig(ROOT / "docs/calibration.png", dpi=130)
    plt.close(fig)
    return {"selected": selected, "samples": len(frame), "evaluations": [{k: v for k, v in e.items() if k not in {"train_matches", "test_matches"}} for e in evaluations]}
