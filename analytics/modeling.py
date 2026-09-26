"""Canonical temporal evaluation and descriptive modeling from notebooks 04-05."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (
    adjusted_rand_score,
    average_precision_score,
    brier_score_loss,
    log_loss,
    mean_absolute_error,
    mean_poisson_deviance,
    roc_auc_score,
    silhouette_score,
)
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, PoissonRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.preprocessing import label_binarize

from analytics.features import CORE_FEATURES, SCENARIO_FEATURES

COUNT_FEATURES = ["hist_corners_per_match", "opp_hist_scr15_conceded_smoothed", "is_home"]
NUMERIC_SCENARIO_FEATURES = [
    "match_minute", "score_diff", "player_difference", "repeat_corner_60s",
    "seconds_since_previous_same_team_corner", "attacking_players", "defending_players",
]
CATEGORICAL_SCENARIO_FEATURES = [
    "match_phase", "game_state", "numerical_state", "corner_side",
]
MODEL_FEATURES = CORE_FEATURES + NUMERIC_SCENARIO_FEATURES + CATEGORICAL_SCENARIO_FEATURES
LOGISTIC_C_VALUES = (0.1, 1.0, 10.0)
POISSON_ALPHAS = (0.01, 0.1, 1.0)
SMOOTHING_ALPHAS = (2.0, 5.0, 10.0, 20.0)
COUNT_MAXIMUM_CONDITIONAL_DISPERSION = 1.5


@dataclass(frozen=True)
class TemporalWindow:
    name: str
    start: pd.Timestamp
    end: pd.Timestamp
    role: str


@dataclass(frozen=True)
class KMeansDescription:
    assignments: pd.DataFrame
    centers: pd.DataFrame
    sensitivity: pd.DataFrame
    model: KMeans


@dataclass(frozen=True)
class DeliveryZoneGate:
    classes: tuple[str, ...]
    support: pd.DataFrame
    persistence_rows: pd.DataFrame
    persistence: float
    chance: float
    passed: bool
    final_start: pd.Timestamp


@dataclass(frozen=True)
class CountDispersionGate:
    raw_dispersion: float
    conditional_dispersion: float
    family: str
    passed: bool


@dataclass(frozen=True)
class CanonicalModelingResult:
    """Complete in-memory stage-05 result, ready for atomic publication."""

    tables: dict[str, pd.DataFrame]
    models: dict[str, BaseEstimator]
    schemas: dict[str, dict[str, Any]]
    winners: list[dict[str, Any]]
    windows: list[TemporalWindow]
    final: TemporalWindow
    count_gate: CountDispersionGate
    zone_gate: DeliveryZoneGate


class ConstantProbabilityModel(BaseEstimator):
    """Serializable league-rate reference with a classifier interface."""

    def fit(self, frame: pd.DataFrame, target: pd.Series) -> "ConstantProbabilityModel":
        self.probability_ = float(np.asarray(target, dtype=float).mean())
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        probability = np.full(len(frame), np.clip(self.probability_, 1e-6, 1 - 1e-6))
        return np.column_stack([1 - probability, probability])


class HistoricalProbabilityModel(BaseEstimator):
    """Use the row's leakage-safe historical probability at inference time."""

    def __init__(
        self, feature: str, *, exposure_feature: str = "history_exposure", alpha: float = 10.0
    ):
        self.feature = feature
        self.exposure_feature = exposure_feature
        self.alpha = alpha

    def fit(self, frame: pd.DataFrame, target: pd.Series) -> "HistoricalProbabilityModel":
        self.league_rate_ = float(np.asarray(target, dtype=float).mean())
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        raw = pd.to_numeric(frame[self.feature], errors="coerce").fillna(self.league_rate_)
        exposure = pd.to_numeric(frame[self.exposure_feature], errors="coerce").fillna(0)
        probability = np.clip(
            (raw.to_numpy(dtype=float) * exposure.to_numpy(dtype=float)
             + self.alpha * self.league_rate_)
            / (exposure.to_numpy(dtype=float) + self.alpha),
            1e-6,
            1 - 1e-6,
        )
        return np.column_stack([1 - probability, probability])


class ConstantCountModel(BaseEstimator):
    """Serializable league-mean count reference."""

    def fit(self, frame: pd.DataFrame, target: pd.Series) -> "ConstantCountModel":
        self.mean_ = float(np.asarray(target, dtype=float).mean())
        return self

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        return np.full(len(frame), max(self.mean_, 1e-6))


class HistoricalCountModel(BaseEstimator):
    """Predict from historical corners per match rather than a fitted dummy."""

    def __init__(self, feature: str = "hist_corners_per_match", *, alpha: float = 10.0):
        self.feature = feature
        self.alpha = alpha

    def fit(self, frame: pd.DataFrame, target: pd.Series) -> "HistoricalCountModel":
        self.league_mean_ = float(np.asarray(target, dtype=float).mean())
        return self

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        history = pd.to_numeric(frame[self.feature], errors="coerce").fillna(self.league_mean_)
        return np.clip(
            (history.to_numpy(dtype=float) * 8 + self.alpha * self.league_mean_)
            / (8 + self.alpha),
            1e-6,
            None,
        )


class ConstantClassModel(BaseEstimator):
    """Serializable multiclass league-frequency reference."""

    def fit(self, frame: pd.DataFrame, target: pd.Series) -> "ConstantClassModel":
        counts = pd.Series(target).value_counts(normalize=True).sort_index()
        self.classes_ = counts.index.to_numpy()
        self.probabilities_ = counts.to_numpy(dtype=float)
        return self

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        return np.tile(self.probabilities_, (len(frame), 1))


class TeamClassModel(BaseEstimator):
    """Historical team-frequency baseline for conditional delivery zones."""

    def fit(self, frame: pd.DataFrame, target: pd.Series) -> "TeamClassModel":
        training = pd.DataFrame({"team": frame["team"].astype(str), "target": target})
        self.classes_ = np.array(sorted(training["target"].unique()))
        global_counts = training["target"].value_counts().reindex(self.classes_, fill_value=0)
        self.global_ = ((global_counts + 1) / (global_counts.sum() + len(self.classes_))).to_numpy()
        self.by_team_: dict[str, np.ndarray] = {}
        for team, group in training.groupby("team"):
            counts = group["target"].value_counts().reindex(self.classes_, fill_value=0)
            self.by_team_[team] = ((counts + self.global_ * 5) / (counts.sum() + 5)).to_numpy()
        return self

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        return np.vstack([self.by_team_.get(str(team), self.global_) for team in frame["team"]])


def descriptive_kmeans(
    corners: pd.DataFrame,
    development_cutoff: str | pd.Timestamp,
    *,
    n_clusters: int = 4,
    k_values: range = range(2, 9),
    seeds: tuple[int, ...] = (7, 21, 42, 84, 168),
    random_state: int = 42,
) -> KMeansDescription:
    """Fit notebook-04 K-Means only on direct deliveries before the cutoff."""
    cutoff = pd.Timestamp(development_cutoff).normalize()
    dates = pd.to_datetime(corners["match_date"]).dt.normalize()
    pool = corners[corners["direct_delivery_valid"] & dates.lt(cutoff)].copy()
    if len(pool) < max(n_clusters, max(k_values)):
        raise ValueError("Insufficient pre-development direct deliveries for K-Means")
    matrix = pool[["end_x", "end_y_relative"]].to_numpy(dtype=float)
    model = KMeans(n_clusters=n_clusters, n_init=20, random_state=random_state).fit(matrix)
    pool["cluster_id"] = model.labels_
    pool["distance_to_center"] = np.linalg.norm(
        matrix - model.cluster_centers_[model.labels_], axis=1
    )
    centers = pd.DataFrame(model.cluster_centers_, columns=["end_x", "end_y_relative"])
    centers.insert(0, "cluster_id", range(n_clusters))
    centers["y_order"] = centers["end_y_relative"].rank(method="first").astype(int)
    centers["geometric_name"] = centers.apply(
        lambda row: f"destino_y{int(row.y_order):02d}_x{int(round(row.end_x)):03d}", axis=1
    )
    centers["n"] = centers["cluster_id"].map(pool["cluster_id"].value_counts())
    centers["fit_before"] = cutoff
    centers["coordinate_transform"] = (
        "end_x unchanged; end_y reflected as 80-end_y for high-side corners"
    )
    pool = pool.merge(
        centers[["cluster_id", "geometric_name"]],
        on="cluster_id",
        how="left",
        validate="many_to_one",
    )
    assignment_columns = [
        "event_id",
        "match_id",
        "match_date",
        "team",
        "cluster_id",
        "geometric_name",
        "distance_to_center",
    ]
    sensitivity_rows: list[dict[str, Any]] = []
    for k in k_values:
        reference = KMeans(n_clusters=k, n_init=20, random_state=random_state).fit(matrix)
        aris = [
            adjusted_rand_score(
                reference.labels_,
                KMeans(n_clusters=k, n_init=20, random_state=seed).fit_predict(matrix),
            )
            for seed in seeds
        ]
        sensitivity_rows.append(
            {
                "k": k,
                "inertia": float(reference.inertia_),
                "silhouette": float(silhouette_score(matrix, reference.labels_)),
                "ari_seed_mean": float(np.mean(aris)),
                "ari_seed_min": float(np.min(aris)),
                "seeds": json.dumps(seeds),
            }
        )
    return KMeansDescription(
        assignments=pool[assignment_columns].copy(),
        centers=centers,
        sensitivity=pd.DataFrame(sensitivity_rows),
        model=model,
    )


def temporal_windows(
    team_match: pd.DataFrame,
    *,
    development_blocks: int = 3,
    initial_fraction: float = 0.40,
    final_fraction: float = 0.15,
) -> tuple[list[TemporalWindow], TemporalWindow]:
    """Derive expanding-origin selection windows and a final confirmation period."""
    eligible = team_match[team_match["pre_match_ready"].fillna(False)]
    dates = np.array(sorted(pd.to_datetime(eligible["match_date"]).dt.normalize().unique()))
    if len(dates) < development_blocks + 2:
        raise ValueError("Insufficient ready dates for temporal windows")
    initial_n = max(8, int(np.floor(len(dates) * initial_fraction)))
    final_n = max(4, int(np.ceil(len(dates) * final_fraction)))
    development = dates[initial_n:-final_n]
    blocks = [block for block in np.array_split(development, development_blocks) if len(block)]
    if len(blocks) != development_blocks:
        raise ValueError("Insufficient development dates for requested blocks")
    windows = [
        TemporalWindow(
            name=f"development_{index}",
            start=pd.Timestamp(block[0]),
            end=pd.Timestamp(block[-1]) + pd.Timedelta(days=1),
            role="selection",
        )
        for index, block in enumerate(blocks, start=1)
    ]
    final = TemporalWindow(
        name="final",
        start=pd.Timestamp(dates[-final_n]),
        end=pd.Timestamp(dates[-1]) + pd.Timedelta(days=1),
        role="confirmation_only",
    )
    if windows[-1].end > final.start:
        raise AssertionError("Development and final windows overlap")
    return windows, final


def temporal_train_test(
    frame: pd.DataFrame, window: TemporalWindow
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return expanding training data and a disjoint temporal test block."""
    dates = pd.to_datetime(frame["match_date"]).dt.normalize()
    train = frame[dates.lt(window.start)].copy()
    test = frame[dates.ge(window.start) & dates.lt(window.end)].copy()
    if train.empty or test.empty:
        raise ValueError(f"Empty train or test partition for {window.name}")
    if "match_id" in frame and not set(train["match_id"]).isdisjoint(test["match_id"]):
        raise AssertionError("A match appears in both temporal partitions")
    if pd.to_datetime(train["match_date"]).max() >= pd.to_datetime(test["match_date"]).min():
        raise AssertionError("Training must be strictly earlier than testing")
    return train, test


def inner_temporal_split(
    train: pd.DataFrame, *, fit_fraction: float = 0.80
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split training dates chronologically for hyperparameter selection."""
    dates = np.array(sorted(pd.to_datetime(train["match_date"]).dt.normalize().unique()))
    if len(dates) < 2:
        raise ValueError("At least two dates are required for an inner split")
    cut_index = min(len(dates) - 1, max(1, int(len(dates) * fit_fraction)))
    cut = pd.Timestamp(dates[cut_index])
    normalized = pd.to_datetime(train["match_date"]).dt.normalize()
    fit = train[normalized.lt(cut)].copy()
    validation = train[normalized.ge(cut)].copy()
    return fit, validation


def binary_metrics(y: pd.Series | np.ndarray, probability: np.ndarray) -> dict[str, Any]:
    """Canonical probabilistic metrics for SCR-15 and short/direct objectives."""
    truth = np.asarray(y, dtype=int)
    predicted = np.clip(np.asarray(probability, dtype=float), 1e-6, 1 - 1e-6)
    return {
        "n": len(truth),
        "positive": int(truth.sum()),
        "prevalence": float(truth.mean()),
        "average_precision": float(average_precision_score(truth, predicted)),
        "brier": float(brier_score_loss(truth, predicted)),
        "log_loss": float(log_loss(truth, predicted)),
        "calibration_gap": float(abs(predicted.mean() - truth.mean())),
        "roc_auc": float(roc_auc_score(truth, predicted)) if len(np.unique(truth)) > 1 else None,
    }


def multiclass_metrics(
    y: pd.Series | np.ndarray, probability: np.ndarray, classes: list[str] | tuple[str, ...]
) -> dict[str, float | int]:
    """Canonical delivery-zone metrics using an explicit development class set."""
    truth = np.asarray(y)
    predicted = np.asarray(probability, dtype=float)
    encoded = label_binarize(truth, classes=classes)
    if len(classes) == 2:
        encoded = np.column_stack([1 - encoded[:, 0], encoded[:, 0]])
    return {
        "n": len(truth),
        "log_loss": float(log_loss(truth, predicted, labels=list(classes))),
        "multiclass_brier": float(np.mean(np.sum((encoded - predicted) ** 2, axis=1))),
        "macro_average_precision": float(
            np.mean(
                [average_precision_score(encoded[:, i], predicted[:, i]) for i in range(len(classes))]
            )
        ),
        "calibration_gap": float(
            np.mean(np.abs(predicted.mean(axis=0) - encoded.mean(axis=0)))
        ),
    }


def count_metrics(y: pd.Series | np.ndarray, prediction: np.ndarray) -> dict[str, float | int]:
    """Canonical corner-count metrics for Poisson-compatible predictions."""
    truth = np.asarray(y, dtype=float)
    predicted = np.clip(np.asarray(prediction, dtype=float), 1e-6, None)
    return {
        "n": len(truth),
        "mae": float(mean_absolute_error(truth, predicted)),
        "poisson_deviance": float(mean_poisson_deviance(truth, predicted)),
    }


def choose_binary_winner(metrics: pd.DataFrame, objective: str) -> tuple[str, pd.DataFrame]:
    """Apply notebook-05's 2-of-3 development-window decision rule."""
    development = metrics[
        metrics["objective"].eq(objective) & metrics["role"].eq("selection")
    ]
    rows: list[dict[str, Any]] = []
    references = ["league_reference", "historical_baseline"]
    for window in development["window"].unique():
        block = development[development["window"].eq(window)].set_index("model")
        available = [name for name in references if name in block.index]
        reference_name = block.loc[available, "log_loss"].idxmin()
        candidate, reference = block.loc["candidate"], block.loc[reference_name]
        passed = (
            candidate["brier"] < reference["brier"]
            and candidate["log_loss"] < reference["log_loss"]
            and candidate["average_precision"] > reference["average_precision"]
            and candidate["calibration_gap"] <= reference["calibration_gap"] + 0.01
        )
        rows.append(
            {
                "objective": objective,
                "window": window,
                "reference": reference_name,
                "quality_better": bool(
                    candidate["brier"] < reference["brier"]
                    and candidate["log_loss"] < reference["log_loss"]
                ),
                "discrimination_better": bool(
                    candidate["average_precision"] > reference["average_precision"]
                ),
                "calibration_not_degraded": bool(
                    candidate["calibration_gap"] <= reference["calibration_gap"] + 0.01
                ),
                "passed": bool(passed),
            }
        )
    checks = pd.DataFrame(rows)
    reference_winner = (
        development[development["model"].isin(references)]
        .groupby("model")["log_loss"]
        .mean()
        .idxmin()
    )
    return ("candidate" if int(checks["passed"].sum()) >= 2 else reference_winner), checks


def choose_multiclass_winner(
    metrics: pd.DataFrame, objective: str = "delivery_zone"
) -> tuple[str, pd.DataFrame]:
    """Apply the canonical 2-of-3 rule to a multiclass objective."""
    development = metrics[
        metrics["objective"].eq(objective) & metrics["role"].eq("selection")
    ]
    rows: list[dict[str, Any]] = []
    references = ["league_reference", "historical_baseline"]
    for window in development["window"].unique():
        block = development[development["window"].eq(window)].set_index("model")
        reference_name = block.loc[references, "log_loss"].idxmin()
        candidate, reference = block.loc["candidate"], block.loc[reference_name]
        passed = (
            candidate["log_loss"] < reference["log_loss"]
            and candidate["multiclass_brier"] < reference["multiclass_brier"]
            and candidate["macro_average_precision"] > reference["macro_average_precision"]
            and candidate["calibration_gap"] <= reference["calibration_gap"] + 0.01
        )
        rows.append(
            {
                "objective": objective,
                "window": window,
                "reference": reference_name,
                "passed": bool(passed),
            }
        )
    checks = pd.DataFrame(rows)
    reference_winner = (
        development[development["model"].isin(references)]
        .groupby("model")["log_loss"]
        .mean()
        .idxmin()
    )
    return ("candidate" if int(checks["passed"].sum()) >= 2 else reference_winner), checks


def choose_count_winner(
    metrics: pd.DataFrame, objective: str = "corner_count"
) -> tuple[str, pd.DataFrame]:
    """Select Poisson only when deviance and MAE improve in at least 2/3 blocks."""
    development = metrics[
        metrics["objective"].eq(objective) & metrics["role"].eq("selection")
    ]
    references = ["league_reference", "historical_baseline"]
    rows: list[dict[str, Any]] = []
    for window in development["window"].unique():
        block = development[development["window"].eq(window)].set_index("model")
        reference_name = block.loc[references, "poisson_deviance"].idxmin()
        candidate, reference = block.loc["candidate"], block.loc[reference_name]
        rows.append(
            {
                "objective": objective,
                "window": window,
                "reference": reference_name,
                "passed": bool(
                    candidate["poisson_deviance"] < reference["poisson_deviance"]
                    and candidate["mae"] < reference["mae"]
                ),
            }
        )
    checks = pd.DataFrame(rows)
    reference_winner = (
        development[development["model"].isin(references)]
        .groupby("model")["poisson_deviance"]
        .mean()
        .idxmin()
    )
    return ("candidate" if int(checks["passed"].sum()) >= 2 else reference_winner), checks


def short_share_persistence(
    observed: pd.DataFrame,
    features: pd.DataFrame,
    final_start: str | pd.Timestamp | None = None,
) -> dict[str, Any]:
    """Compare historical short share with the next observed team-match share."""
    habit = observed.merge(
        features,
        on=["match_id", "match_date", "team", "opponent", "is_home"],
        how="left",
        validate="one_to_one",
        suffixes=("", "_history"),
    )
    habit = habit[habit["pre_match_ready"].fillna(False) & habit["n_corners"].gt(0)].copy()
    if final_start is not None:
        habit = habit[
            pd.to_datetime(habit["match_date"]).dt.normalize()
            < pd.Timestamp(final_start).normalize()
        ].copy()
    habit["current_short_share"] = habit["n_short"] / habit["n_corners"]
    rho = habit["hist_short_share"].corr(habit["current_short_share"], method="spearman")
    return {
        "habit": "short_share",
        "n_team_matches": len(habit),
        "statistic": "spearman_rho",
        "value": float(rho),
        "interpretation": "historical share versus next team-match share",
    }


def count_dispersion_gate(
    count_data: pd.DataFrame,
    first_development_start: str | pd.Timestamp,
    features: list[str] | tuple[str, ...],
    *,
    maximum_conditional_dispersion: float = 1.5,
) -> CountDispersionGate:
    """Fit the notebook Poisson probe and reject unsupported count families."""
    cutoff = pd.Timestamp(first_development_start).normalize()
    dates = pd.to_datetime(count_data["match_date"]).dt.normalize()
    train = count_data[dates.lt(cutoff)].copy()
    if train.empty:
        raise ValueError("No observations before the first development window")
    mean = float(train["n_corners"].mean())
    if mean <= 0:
        raise ValueError("Corner-count mean must be positive")
    raw = float(train["n_corners"].var(ddof=1) / mean)
    model = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("model", PoissonRegressor(alpha=0.1, max_iter=1000)),
        ]
    )
    model.fit(train[list(features)], train["n_corners"])
    predicted = np.clip(model.predict(train[list(features)]), 1e-6, None)
    degrees = max(1, len(train) - len(features) - 1)
    conditional = float(
        np.sum((train["n_corners"].to_numpy() - predicted) ** 2 / predicted) / degrees
    )
    passed = conditional <= maximum_conditional_dispersion
    return CountDispersionGate(
        raw_dispersion=raw,
        conditional_dispersion=conditional,
        family="poisson" if passed else "negative_binomial_required",
        passed=passed,
    )


def delivery_zone_gate(
    zone_data: pd.DataFrame,
    features: pd.DataFrame,
    corners: pd.DataFrame,
    final_start: str | pd.Timestamp,
    *,
    minimum_total: int = 100,
    minimum_teams: int = 10,
) -> DeliveryZoneGate:
    """Assess support and persistence without consulting the final period.

    Classes, support, team support, persistence rows, majority chance and the
    decision all derive exclusively from rows with ``match_date < final_start``.
    """
    cutoff = pd.Timestamp(final_start).normalize()
    zone_dates = pd.to_datetime(zone_data["match_date"]).dt.normalize()
    development_zone = zone_data[
        zone_dates.lt(cutoff) & zone_data["pre_match_ready"].fillna(False)
    ].copy()
    classes = tuple(sorted(development_zone["delivery_zone"].dropna().unique().tolist()))
    if not classes:
        return DeliveryZoneGate(
            classes=(),
            support=pd.DataFrame(columns=["delivery_zone", "n", "teams"]),
            persistence_rows=pd.DataFrame(),
            persistence=float("nan"),
            chance=float("nan"),
            passed=False,
            final_start=cutoff,
        )

    support_total = development_zone["delivery_zone"].value_counts().reindex(classes, fill_value=0)
    support_teams = (
        development_zone.groupby("delivery_zone")["team"].nunique().reindex(classes, fill_value=0)
    )
    support = pd.DataFrame(
        {"delivery_zone": classes, "n": support_total.values, "teams": support_teams.values}
    )

    feature_dates = pd.to_datetime(features["match_date"]).dt.normalize()
    eligible_features = features[
        features["pre_match_ready"].fillna(False) & feature_dates.lt(cutoff)
    ]
    corner_dates = pd.to_datetime(corners["match_date"]).dt.normalize()
    direct = corners[
        corners["direct_delivery_valid"].fillna(False) & corner_dates.lt(cutoff)
    ]
    rows: list[dict[str, Any]] = []
    for row in eligible_features.itertuples(index=False):
        history_ids = json.loads(row.history_match_ids)
        historical = direct[
            direct["match_id"].isin(history_ids) & direct["team"].eq(row.team)
        ]
        current = direct[
            direct["match_id"].eq(row.match_id) & direct["team"].eq(row.team)
        ]
        if current.empty:
            continue
        historical_counts = historical["delivery_zone"].value_counts()
        current_counts = current["delivery_zone"].value_counts()
        historical_top = historical_counts.idxmax() if len(historical_counts) else None
        current_top = current_counts.idxmax()
        rows.append(
            {
                "match_id": row.match_id,
                "match_date": pd.Timestamp(row.match_date).normalize(),
                "team": row.team,
                "historical_top_zone": historical_top,
                "current_top_zone": current_top,
                "same_top_zone": historical_top == current_top,
                **{
                    f"hist_zone_count_{name}": int(historical_counts.get(name, 0))
                    for name in classes
                },
            }
        )
    persistence_rows = pd.DataFrame(rows)
    if persistence_rows.empty:
        persistence = chance = float("nan")
        persistence_passed = False
    else:
        persistence = float(persistence_rows["same_top_zone"].mean())
        chance = float(
            persistence_rows["current_top_zone"].value_counts(normalize=True).max()
        )
        persistence_passed = persistence > chance
    passed = bool(
        support["n"].min() >= minimum_total
        and support["teams"].min() >= minimum_teams
        and persistence_passed
    )
    return DeliveryZoneGate(
        classes=classes,
        support=support,
        persistence_rows=persistence_rows,
        persistence=persistence,
        chance=chance,
        passed=passed,
        final_start=cutoff,
    )


def logistic_pipeline(features: list[str], *, c: float = 1.0) -> Pipeline:
    """Build the regularized LR candidate used by binary and zone objectives."""
    categorical = [name for name in features if name in CATEGORICAL_SCENARIO_FEATURES]
    numeric = [name for name in features if name not in categorical]
    transformers: list[tuple[str, Pipeline, list[str]]] = []
    if numeric:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    [("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]
                ),
                numeric,
            )
        )
    if categorical:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("one_hot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            )
        )
    return Pipeline(
        [
            ("preprocess", ColumnTransformer(transformers)),
            ("model", LogisticRegression(C=c, max_iter=2000, random_state=42)),
        ]
    )


def poisson_pipeline(features: list[str], *, alpha: float = 0.1) -> Pipeline:
    """Build the regularized Poisson candidate for team-match corner counts."""
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("model", PoissonRegressor(alpha=alpha, max_iter=1000)),
        ]
    )


def _eligible(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame[frame["pre_match_ready"].fillna(False)].copy()
    result["match_date"] = pd.to_datetime(result["match_date"]).dt.normalize()
    return result


def tune_binary_smoothing(
    train: pd.DataFrame,
    *,
    target: str,
    raw_feature: str,
    exposure_feature: str = "history_exposure",
) -> tuple[float, pd.DataFrame]:
    """Tune historical-rate shrinkage on the inner chronological split."""
    fit, validation = inner_temporal_split(train)
    prior = float(fit[target].mean())
    rows: list[dict[str, float | str]] = []
    for alpha in SMOOTHING_ALPHAS:
        raw = pd.to_numeric(validation[raw_feature], errors="coerce").fillna(prior)
        exposure = pd.to_numeric(validation[exposure_feature], errors="coerce").fillna(0)
        probability = (raw * exposure + alpha * prior) / (exposure + alpha)
        rows.append(
            {"parameter": "smoothing_alpha", "value": alpha, "alpha": alpha,
             "inner_log_loss": binary_metrics(validation[target], probability)["log_loss"]}
        )
    result = pd.DataFrame(rows)
    best = result.sort_values(["inner_log_loss", "value"]).iloc[0]
    return float(best["value"]), result


def tune_count_smoothing(train: pd.DataFrame) -> tuple[float, pd.DataFrame]:
    """Tune the notebook's eight-match historical count reference."""
    fit, validation = inner_temporal_split(train)
    prior = float(fit["n_corners"].mean())
    rows: list[dict[str, float | str]] = []
    for alpha in SMOOTHING_ALPHAS:
        prediction = (
            validation["hist_corners_per_match"].to_numpy(dtype=float) * 8 + alpha * prior
        ) / (8 + alpha)
        rows.append(
            {"parameter": "smoothing_alpha", "value": alpha, "alpha": alpha,
             "inner_mae": float(mean_absolute_error(validation["n_corners"], prediction))}
        )
    result = pd.DataFrame(rows)
    best = result.sort_values(["inner_mae", "value"]).iloc[0]
    return float(best["value"]), result


def evaluate_binary_temporally(
    frame: pd.DataFrame,
    *,
    objective: str,
    target: str,
    historical_feature: str,
    feature_sets: dict[str, list[str]],
    windows: list[TemporalWindow],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Tune LR inside each training partition and evaluate all references."""
    data = _eligible(frame)
    metric_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    tuning_rows: list[dict[str, Any]] = []
    for window in windows:
        train, test = temporal_train_test(data, window)
        fit, validation = inner_temporal_split(train)
        for feature_set, features in feature_sets.items():
            for c in LOGISTIC_C_VALUES:
                model = logistic_pipeline(features, c=c)
                model.fit(fit[features], fit[target].astype(int))
                probability = model.predict_proba(validation[features])[:, 1]
                tuning_rows.append(
                    {
                        "objective": objective,
                        "window": window.name,
                        "role": window.role,
                        "feature_set": feature_set,
                        "parameter": "C",
                        "value": c,
                        "C": c,
                        "inner_log_loss": binary_metrics(validation[target], probability)["log_loss"],
                    }
                )
        smoothing_alpha, smoothing = tune_binary_smoothing(
            train, target=target, raw_feature=historical_feature
        )
        for row in smoothing.to_dict("records"):
            tuning_rows.append(
                {"objective": objective, "window": window.name, "role": window.role,
                 "feature_set": None, **row}
            )
        tuning = pd.DataFrame(tuning_rows)
        current = tuning[
            tuning["window"].eq(window.name) & tuning["parameter"].eq("C")
        ]
        best = current.loc[current["inner_log_loss"].idxmin()]
        selected_features = feature_sets[str(best["feature_set"])]
        candidate = logistic_pipeline(selected_features, c=float(best["value"]))
        candidate.fit(train[selected_features], train[target].astype(int))
        models: dict[str, BaseEstimator] = {
            "league_reference": ConstantProbabilityModel().fit(train, train[target]),
            "historical_baseline": HistoricalProbabilityModel(
                historical_feature, alpha=smoothing_alpha
            ).fit(train, train[target]),
            "candidate": candidate,
        }
        probabilities = {
            "league_reference": models["league_reference"].predict_proba(test)[:, 1],
            "historical_baseline": models["historical_baseline"].predict_proba(test)[:, 1],
            "candidate": candidate.predict_proba(test[selected_features])[:, 1],
        }
        for name, probability in probabilities.items():
            metric_rows.append(
                {
                    "objective": objective,
                    "window": window.name,
                    "role": window.role,
                    "model": name,
                    **binary_metrics(test[target], probability),
                }
            )
        identifiers = [name for name in ["event_id", "match_id", "match_date", "team"] if name in test]
        for position, (_, row) in enumerate(test.iterrows()):
            prediction_rows.append(
                {
                    **{name: row[name] for name in identifiers},
                    target: int(row[target]),
                    "window": window.name,
                    **{f"p_{name}": values[position] for name, values in probabilities.items()},
                }
            )
    return pd.DataFrame(metric_rows), pd.DataFrame(prediction_rows), pd.DataFrame(tuning_rows)


def evaluate_count_temporally(
    frame: pd.DataFrame,
    *,
    windows: list[TemporalWindow],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Tune Poisson chronologically and evaluate count references."""
    data = _eligible(frame)
    metric_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    tuning_rows: list[dict[str, Any]] = []
    for window in windows:
        train, test = temporal_train_test(data, window)
        fit, validation = inner_temporal_split(train)
        smoothing_alpha, smoothing = tune_count_smoothing(train)
        for row in smoothing.to_dict("records"):
            tuning_rows.append(
                {"objective": "corner_count", "window": window.name, "role": window.role,
                 "feature_set": None, **row}
            )
        for alpha in POISSON_ALPHAS:
            model = poisson_pipeline(COUNT_FEATURES, alpha=alpha)
            model.fit(fit[COUNT_FEATURES], fit["n_corners"])
            prediction = model.predict(validation[COUNT_FEATURES])
            tuning_rows.append(
                {
                    "objective": "corner_count",
                    "window": window.name,
                    "role": window.role,
                    "parameter": "poisson_alpha",
                    "value": alpha,
                    "alpha": alpha,
                    "inner_deviance": count_metrics(validation["n_corners"], prediction)[
                        "poisson_deviance"
                    ],
                }
            )
        current = pd.DataFrame(tuning_rows)
        current = current[
            current["window"].eq(window.name)
            & current["parameter"].eq("poisson_alpha")
        ]
        alpha = float(current.loc[current["inner_deviance"].idxmin(), "value"])
        candidate = poisson_pipeline(COUNT_FEATURES, alpha=alpha)
        candidate.fit(train[COUNT_FEATURES], train["n_corners"])
        references: dict[str, BaseEstimator] = {
            "league_reference": ConstantCountModel().fit(train, train["n_corners"]),
            "historical_baseline": HistoricalCountModel(alpha=smoothing_alpha).fit(
                train, train["n_corners"]
            ),
        }
        predictions = {
            "league_reference": references["league_reference"].predict(test),
            "historical_baseline": references["historical_baseline"].predict(test),
            "candidate": candidate.predict(test[COUNT_FEATURES]),
        }
        for name, prediction in predictions.items():
            metric_rows.append(
                {
                    "objective": "corner_count",
                    "window": window.name,
                    "role": window.role,
                    "model": name,
                    **count_metrics(test["n_corners"], prediction),
                }
            )
        for position, (_, row) in enumerate(test.iterrows()):
            prediction_rows.append(
                {
                    "match_id": row["match_id"],
                    "match_date": row["match_date"],
                    "team": row["team"],
                    "n_corners": int(row["n_corners"]),
                    "window": window.name,
                    **{
                        f"prediction_{name}": values[position]
                        for name, values in predictions.items()
                    },
                }
            )
    return pd.DataFrame(metric_rows), pd.DataFrame(prediction_rows), pd.DataFrame(tuning_rows)


def _selection_spec(
    tuning: pd.DataFrame, objective: str, feature_sets: dict[str, list[str]] | None = None
) -> tuple[list[str], float]:
    development = tuning[
        tuning["objective"].eq(objective) & tuning["role"].eq("selection")
    ]
    parameter = "C" if feature_sets is not None else "poisson_alpha"
    development = development[development["parameter"].eq(parameter)]
    score = "inner_log_loss" if feature_sets is not None else "inner_deviance"
    group = ["value"] + (["feature_set"] if feature_sets is not None else [])
    best = development.groupby(group, dropna=False)[score].mean().idxmin()
    if feature_sets is None:
        return COUNT_FEATURES, float(best)
    value, feature_set = best
    return feature_sets[str(feature_set)], float(value)


def _selection_smoothing(tuning: pd.DataFrame, objective: str) -> float:
    development = tuning[
        tuning["objective"].eq(objective)
        & tuning["role"].eq("selection")
        & tuning["parameter"].eq("smoothing_alpha")
    ]
    score = "inner_mae" if objective == "corner_count" else "inner_log_loss"
    return float(development.groupby("value")[score].mean().idxmin())


def _fit_binary_artifacts(
    frame: pd.DataFrame,
    *,
    target: str,
    historical_feature: str,
    winner: str,
    features: list[str],
    c: float,
    smoothing_alpha: float,
    final_start: pd.Timestamp,
) -> tuple[BaseEstimator, BaseEstimator, BaseEstimator, BaseEstimator]:
    data = _eligible(frame)
    retrospective = data[data["match_date"].lt(final_start)]
    candidate_retrospective = logistic_pipeline(features, c=c).fit(
        retrospective[features], retrospective[target].astype(int)
    )
    candidate_full = logistic_pipeline(features, c=c).fit(
        data[features], data[target].astype(int)
    )

    def selected(training: pd.DataFrame) -> BaseEstimator:
        if winner == "candidate":
            return logistic_pipeline(features, c=c).fit(training[features], training[target].astype(int))
        if winner == "historical_baseline":
            return HistoricalProbabilityModel(
                historical_feature, alpha=smoothing_alpha
            ).fit(training, training[target])
        return ConstantProbabilityModel().fit(training, training[target])

    return candidate_retrospective, candidate_full, selected(retrospective), selected(data)


def _fit_count_artifacts(
    frame: pd.DataFrame,
    *,
    winner: str,
    alpha: float,
    smoothing_alpha: float,
    final_start: pd.Timestamp,
) -> tuple[BaseEstimator, BaseEstimator, BaseEstimator, BaseEstimator]:
    data = _eligible(frame)
    retrospective = data[data["match_date"].lt(final_start)]
    candidate_retrospective = poisson_pipeline(COUNT_FEATURES, alpha=alpha).fit(
        retrospective[COUNT_FEATURES], retrospective["n_corners"]
    )
    candidate_full = poisson_pipeline(COUNT_FEATURES, alpha=alpha).fit(
        data[COUNT_FEATURES], data["n_corners"]
    )

    def selected(training: pd.DataFrame) -> BaseEstimator:
        if winner == "candidate":
            return poisson_pipeline(COUNT_FEATURES, alpha=alpha).fit(
                training[COUNT_FEATURES], training["n_corners"]
            )
        if winner == "historical_baseline":
            return HistoricalCountModel(alpha=smoothing_alpha).fit(
                training, training["n_corners"]
            )
        return ConstantCountModel().fit(training, training["n_corners"])

    return candidate_retrospective, candidate_full, selected(retrospective), selected(data)


def _fit_zone_artifacts(
    frame: pd.DataFrame,
    *,
    winner: str,
    c: float,
    final_start: pd.Timestamp,
) -> tuple[BaseEstimator, BaseEstimator, BaseEstimator, BaseEstimator]:
    data = _eligible(frame)
    retrospective = data[data["match_date"].lt(final_start)]
    candidate_retrospective = logistic_pipeline(MODEL_FEATURES, c=c).fit(
        retrospective[MODEL_FEATURES], retrospective["delivery_zone"]
    )
    candidate_full = logistic_pipeline(MODEL_FEATURES, c=c).fit(
        data[MODEL_FEATURES], data["delivery_zone"]
    )

    def selected(training: pd.DataFrame) -> BaseEstimator:
        if winner == "candidate":
            return logistic_pipeline(MODEL_FEATURES, c=c).fit(
                training[MODEL_FEATURES], training["delivery_zone"]
            )
        if winner == "historical_baseline":
            return TeamClassModel().fit(training, training["delivery_zone"])
        return ConstantClassModel().fit(training, training["delivery_zone"])

    return candidate_retrospective, candidate_full, selected(retrospective), selected(data)


def bootstrap_prediction_deltas(
    predictions: pd.DataFrame,
    *,
    objective: str,
    target: str,
    checks: pd.DataFrame,
    iterations: int = 200,
    random_state: int = 42,
) -> pd.DataFrame:
    """Resample complete matches when comparing candidate and best reference."""
    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(random_state)
    for window, group in predictions.groupby("window"):
        check = checks[checks["window"].eq(window)]
        if check.empty:
            continue
        reference = str(check.iloc[0]["reference"])
        match_ids = group["match_id"].drop_duplicates().to_numpy()
        for iteration in range(iterations):
            sampled = rng.choice(match_ids, size=len(match_ids), replace=True)
            sample = pd.concat([group[group["match_id"].eq(match)] for match in sampled])
            if objective == "corner_count":
                candidate = count_metrics(sample[target], sample["prediction_candidate"])
                baseline = count_metrics(sample[target], sample[f"prediction_{reference}"])
                values = {
                    "mae_delta": candidate["mae"] - baseline["mae"],
                    "deviance_delta": candidate["poisson_deviance"] - baseline["poisson_deviance"],
                }
            else:
                candidate = binary_metrics(sample[target], sample["p_candidate"])
                baseline = binary_metrics(sample[target], sample[f"p_{reference}"])
                values = {
                    "brier_delta": candidate["brier"] - baseline["brier"],
                    "ap_delta": candidate["average_precision"] - baseline["average_precision"],
                }
            rows.append(
                {"objective": objective, "window": window, "iteration": iteration, **values}
            )
    return pd.DataFrame(rows)


def run_canonical_modeling(
    tables: dict[str, pd.DataFrame],
    *,
    bootstrap_iterations: int = 200,
) -> CanonicalModelingResult:
    """Recreate stage 05 without notebooks and without using K-Means as a predictor."""
    count_data = _eligible(tables["model_corner_count"])
    development, final = temporal_windows(count_data)
    windows = [*development, final]
    if any(window.end > final.start for window in development):
        raise AssertionError("Development windows overlap the final period")

    scenario = {
        "pre_match": list(CORE_FEATURES),
        "pre_match_plus_scenario": list(MODEL_FEATURES),
    }
    scr_data = tables["model_scr15_scenario"].merge(
        tables["pre_match_features"][["match_id", "team", "hist_scr15_raw"]],
        on=["match_id", "team"], how="left", validate="many_to_one",
    )
    scr_data["history_exposure"] = (
        scr_data["hist_corners_per_match"] * 8
    ).round().clip(lower=1)
    short_data = tables["model_short_direct"].copy()
    short_data["history_exposure"] = (
        short_data["hist_corners_per_match"] * 8
    ).round().clip(lower=1)
    scr_metrics, scr_predictions, scr_tuning = evaluate_binary_temporally(
        scr_data, objective="scr15", target="shot_within_15s",
        historical_feature="hist_scr15_raw", feature_sets=scenario, windows=windows,
    )
    short_metrics, short_predictions, short_tuning = evaluate_binary_temporally(
        short_data, objective="short_direct", target="short_proxy",
        historical_feature="hist_short_share", feature_sets={"pre_kick": MODEL_FEATURES},
        windows=windows,
    )
    count_gate = count_dispersion_gate(
        count_data, development[0].start, COUNT_FEATURES,
        maximum_conditional_dispersion=COUNT_MAXIMUM_CONDITIONAL_DISPERSION,
    )
    if not count_gate.passed:
        raise ValueError(
            f"Poisson gate failed before first development window: conditional dispersion={count_gate.conditional_dispersion:.3f}"
        )
    count_metrics_frame, count_predictions, count_tuning = evaluate_count_temporally(
        count_data, windows=windows
    )
    metrics = pd.concat([scr_metrics, short_metrics, count_metrics_frame], ignore_index=True)
    tuning = pd.concat([scr_tuning, short_tuning, count_tuning], ignore_index=True, sort=False)

    scr_winner, scr_checks = choose_binary_winner(metrics, "scr15")
    short_winner, short_checks = choose_binary_winner(metrics, "short_direct")
    count_winner, count_checks = choose_count_winner(metrics)
    short_habit = short_share_persistence(
        tables["team_match_observed"], tables["pre_match_features"], final.start
    )
    zone_gate = delivery_zone_gate(
        tables["model_delivery_zone"], tables["pre_match_features"],
        tables["corners_engineered"], final.start,
    )
    zone_habit = {
        "habit": "dominant_delivery_zone",
        "n_team_matches": len(zone_gate.persistence_rows),
        "statistic": "top_zone_accuracy",
        "value": zone_gate.persistence,
        "comparison": zone_gate.chance,
        "interpretation": "historical dominant zone versus next; comparison is majority-class chance",
    }
    short_habit["comparison"] = np.nan

    zone_checks = pd.DataFrame(
        [{
            "objective": "delivery_zone", "window": None, "reference": None,
            "passed": zone_gate.passed,
            "reason": None if zone_gate.passed else "support or persistence gate failed",
        }]
    )
    zone_winner = "not_modeled"
    zone_metrics = pd.DataFrame()
    zone_predictions = pd.DataFrame()
    if zone_gate.passed:
        zone_metrics, zone_predictions, zone_tuning = _evaluate_zone_temporally(
            tables["model_delivery_zone"], windows, zone_gate.classes
        )
        tuning = pd.concat([tuning, zone_tuning], ignore_index=True, sort=False)
        metrics = pd.concat([metrics, zone_metrics], ignore_index=True, sort=False)
        zone_winner, zone_checks = choose_multiclass_winner(metrics)

    checks = pd.concat([scr_checks, short_checks, zone_checks, count_checks], ignore_index=True, sort=False)
    winners = [
        {
            "objective": "scr15", "winner": scr_winner, "modeled": True,
            "justification": f"candidate passed {int(scr_checks.passed.sum())}/3 development windows",
        },
        {
            "objective": "short_direct", "winner": short_winner, "modeled": True,
            "justification": f"candidate passed {int(short_checks.passed.sum())}/3 development windows; persistence rho={short_habit['value']:.3f}",
        },
        {
            "objective": "delivery_zone", "winner": zone_winner, "modeled": zone_gate.passed,
            "justification": f"support min={int(zone_gate.support.n.min()) if len(zone_gate.support) else 0}, teams min={int(zone_gate.support.teams.min()) if len(zone_gate.support) else 0}, persistence={zone_gate.persistence:.3f} vs {zone_gate.chance:.3f}",
        },
        {
            "objective": "corner_count", "winner": count_winner, "modeled": True,
            "justification": f"variance/mean={count_gate.raw_dispersion:.3f}; conditional dispersion={count_gate.conditional_dispersion:.3f}; family={count_gate.family}",
        },
    ]

    scr_features, scr_c = _selection_spec(scr_tuning, "scr15", scenario)
    short_features, short_c = _selection_spec(
        short_tuning, "short_direct", {"pre_kick": MODEL_FEATURES}
    )
    _, count_alpha = _selection_spec(count_tuning, "corner_count")
    scr_smoothing = _selection_smoothing(scr_tuning, "scr15")
    short_smoothing = _selection_smoothing(short_tuning, "short_direct")
    count_smoothing = _selection_smoothing(count_tuning, "corner_count")
    models: dict[str, BaseEstimator] = {}
    fitted_objectives = {
        "scr15": _fit_binary_artifacts(
            scr_data, target="shot_within_15s",
            historical_feature="hist_scr15_raw", winner=scr_winner,
            features=scr_features, c=scr_c, smoothing_alpha=scr_smoothing,
            final_start=final.start,
        ),
        "short_direct": _fit_binary_artifacts(
            short_data, target="short_proxy",
            historical_feature="hist_short_share", winner=short_winner,
            features=short_features, c=short_c, smoothing_alpha=short_smoothing,
            final_start=final.start,
        ),
        "corner_count": _fit_count_artifacts(
            count_data, winner=count_winner, alpha=count_alpha,
            smoothing_alpha=count_smoothing, final_start=final.start,
        ),
    }
    if zone_gate.passed:
        _, zone_c = _selection_spec(
            zone_tuning, "delivery_zone", {"pre_match_plus_scenario": MODEL_FEATURES}
        )
        fitted_objectives["delivery_zone"] = _fit_zone_artifacts(
            tables["model_delivery_zone"], winner=zone_winner, c=zone_c,
            final_start=final.start,
        )
    for objective, fitted in fitted_objectives.items():
        for suffix, model in zip(
            ["candidate_retrospective", "candidate_refit_full", "selected_retrospective", "selected_refit_full"],
            fitted,
        ):
            models[f"{objective}_{suffix}.joblib"] = model

    window_rows = []
    for window in windows:
        train, test = temporal_train_test(count_data, window)
        window_rows.append(
            {"name": window.name, "start": window.start, "end": window.end, "role": window.role,
             "train_rows_team_match": len(train), "test_rows_team_match": len(test)}
        )
    bootstrap = pd.concat(
        [
            bootstrap_prediction_deltas(
                scr_predictions[scr_predictions.window.ne("final")], objective="scr15",
                target="shot_within_15s", checks=scr_checks,
                iterations=bootstrap_iterations, random_state=42,
            ),
            bootstrap_prediction_deltas(
                short_predictions[short_predictions.window.ne("final")], objective="short_direct",
                target="short_proxy", checks=short_checks,
                iterations=bootstrap_iterations, random_state=43,
            ),
            bootstrap_prediction_deltas(
                count_predictions[count_predictions.window.ne("final")], objective="corner_count",
                target="n_corners", checks=count_checks,
                iterations=bootstrap_iterations, random_state=44,
            ),
        ],
        ignore_index=True,
        sort=False,
    )
    tables_out = {
        "temporal_windows": pd.DataFrame(window_rows),
        "habit_persistence": pd.DataFrame([short_habit, zone_habit]),
        "temporal_metrics": metrics,
        "selection_checks": checks,
        "bootstrap_by_match": bootstrap,
        "tuning_development": tuning,
        "objective_winners": pd.DataFrame(winners),
        "zone_support": zone_gate.support,
        "scr15_predictions": scr_predictions,
        "short_predictions": short_predictions,
        "count_predictions": count_predictions,
    }
    if zone_gate.passed:
        tables_out["zone_predictions"] = zone_predictions
    schemas = {
        "scr15_input_schema.json": _schema("scr15", "shot_within_15s", scr_features, scr_winner, final),
        "short_direct_input_schema.json": _schema("short_direct", "short_proxy", short_features, short_winner, final),
        "corner_count_input_schema.json": _schema("corner_count", "n_corners", COUNT_FEATURES, count_winner, final, family="poisson"),
        "scr15_selected_input_schema.json": _selected_schema(
            "scr15", scr_winner, scr_features,
            ["hist_scr15_raw", "history_exposure"], final,
        ),
        "short_direct_selected_input_schema.json": _selected_schema(
            "short_direct", short_winner, short_features,
            ["hist_short_share", "history_exposure"], final,
        ),
        "corner_count_selected_input_schema.json": _selected_schema(
            "corner_count", count_winner, COUNT_FEATURES, "hist_corners_per_match", final
        ),
    }
    if zone_gate.passed:
        schemas["delivery_zone_input_schema.json"] = _schema(
            "delivery_zone", "delivery_zone", MODEL_FEATURES, zone_winner, final,
            classes=list(zone_gate.classes),
        )
        schemas["delivery_zone_selected_input_schema.json"] = _selected_schema(
            "delivery_zone", zone_winner, MODEL_FEATURES, "team", final
        )
    return CanonicalModelingResult(
        tables=tables_out, models=models, schemas=schemas, winners=winners,
        windows=development, final=final, count_gate=count_gate, zone_gate=zone_gate,
    )


def _schema(
    objective: str, target: str, features: list[str], winner: str,
    final: TemporalWindow, **extra: Any,
) -> dict[str, Any]:
    return {
        "objective": objective, "target": target, "input_columns": features,
        "retrospective_trained_before": final.start.date().isoformat(),
        "refit_full_evaluation_status": "not retrospectively evaluated",
        "winner": winner, **extra,
    }


def _selected_schema(
    objective: str, winner: str, candidate_features: list[str],
    historical_feature: str | list[str], final: TemporalWindow,
) -> dict[str, Any]:
    historical_features = (
        [historical_feature] if isinstance(historical_feature, str) else historical_feature
    )
    features = candidate_features if winner == "candidate" else (
        historical_features if winner == "historical_baseline" else []
    )
    return {
        "objective": objective, "winner": winner, "input_columns": features,
        "pipeline": "selected model with its required preprocessing; references remain functional estimators",
        "retrospective_trained_before": final.start.date().isoformat(),
        "refit_full_evaluation_status": "not retrospectively evaluated",
    }


def _evaluate_zone_temporally(
    frame: pd.DataFrame,
    windows: list[TemporalWindow],
    classes: tuple[str, ...],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Evaluate conditional delivery-zone LR only after its pre-final gate passes."""
    data = _eligible(frame)
    metrics_rows: list[dict[str, Any]] = []
    predictions_rows: list[dict[str, Any]] = []
    tuning_rows: list[dict[str, Any]] = []
    for window in windows:
        train, test = temporal_train_test(data, window)
        train = train[train["delivery_zone"].isin(classes)]
        test = test[test["delivery_zone"].isin(classes)]
        fit, validation = inner_temporal_split(train)
        for c in LOGISTIC_C_VALUES:
            model = logistic_pipeline(MODEL_FEATURES, c=c).fit(
                fit[MODEL_FEATURES], fit["delivery_zone"]
            )
            probability = model.predict_proba(validation[MODEL_FEATURES])
            tuning_rows.append(
                {"objective": "delivery_zone", "window": window.name, "role": window.role,
                 "feature_set": "pre_match_plus_scenario", "parameter": "C", "value": c,
                 "C": c,
                 "inner_log_loss": multiclass_metrics(validation["delivery_zone"], probability, classes)["log_loss"]}
            )
        current = pd.DataFrame(tuning_rows)
        current = current[current.window.eq(window.name)]
        c = float(current.loc[current.inner_log_loss.idxmin(), "value"])
        candidate = logistic_pipeline(MODEL_FEATURES, c=c).fit(
            train[MODEL_FEATURES], train["delivery_zone"]
        )
        references = {
            "league_reference": ConstantClassModel().fit(train, train["delivery_zone"]),
            "historical_baseline": TeamClassModel().fit(train, train["delivery_zone"]),
        }
        probabilities = {
            "league_reference": references["league_reference"].predict_proba(test),
            "historical_baseline": references["historical_baseline"].predict_proba(test),
            "candidate": candidate.predict_proba(test[MODEL_FEATURES]),
        }
        for name, probability in probabilities.items():
            model_classes = candidate.classes_ if name == "candidate" else references[name].classes_
            order = [int(np.where(model_classes == label)[0][0]) for label in classes]
            ordered = probability[:, order]
            metrics_rows.append(
                {"objective": "delivery_zone", "window": window.name, "role": window.role,
                 "model": name, **multiclass_metrics(test["delivery_zone"], ordered, classes)}
            )
        for position, (_, row) in enumerate(test.iterrows()):
            predictions_rows.append(
                {"event_id": row["event_id"], "match_id": row["match_id"],
                 "match_date": row["match_date"], "team": row["team"],
                 "delivery_zone": row["delivery_zone"], "window": window.name,
                 **{f"p_candidate_{label}": probabilities["candidate"][position, list(candidate.classes_).index(label)] for label in classes}}
            )
    return pd.DataFrame(metrics_rows), pd.DataFrame(predictions_rows), pd.DataFrame(tuning_rows)
