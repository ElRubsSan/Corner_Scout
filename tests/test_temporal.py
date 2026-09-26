import pandas as pd

from analytics.features import select_prior_matches
from analytics.modeling import temporal_train_test, temporal_windows


def test_prior_selector_excludes_same_date_and_future_matches() -> None:
    frame = pd.DataFrame(
        {
            "match_id": range(1, 12),
            "match_date": ["2015-01-01"] * 8 + ["2015-01-02"] * 3,
            "kick_off": [f"{hour:02d}:00" for hour in range(11)],
            "team": ["A"] * 11,
        }
    )
    result = select_prior_matches(frame, "A", "2015-01-02")

    assert result.match_id.tolist() == list(range(1, 9))
    assert (pd.to_datetime(result.match_date) < pd.Timestamp("2015-01-02")).all()


def test_temporal_windows_are_disjoint_and_final_is_confirmation_only() -> None:
    frame = pd.DataFrame(
        {
            "match_id": range(30),
            "match_date": pd.date_range("2015-01-01", periods=30),
            "pre_match_ready": True,
        }
    )
    windows, final = temporal_windows(frame)

    assert len(windows) == 3
    assert all(window.role == "selection" for window in windows)
    assert final.role == "confirmation_only"
    assert windows[-1].end <= final.start
    train, test = temporal_train_test(frame, final)
    assert train.match_date.max() < test.match_date.min()
    assert set(train.match_id).isdisjoint(test.match_id)


def test_equal_to_window_start_never_enters_training() -> None:
    frame = pd.DataFrame(
        {
            "match_id": range(30),
            "match_date": pd.date_range("2015-01-01", periods=30),
            "pre_match_ready": True,
        }
    )
    _, final = temporal_windows(frame)
    train, test = temporal_train_test(frame, final)

    assert not (pd.to_datetime(train.match_date) == final.start).any()
    assert (pd.to_datetime(test.match_date) == final.start).any()
