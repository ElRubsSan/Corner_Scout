import pandas as pd
from analytics.io import data_dir
from analytics.models import features, previous_matches


def test_future_outcomes_cannot_change_past_features():
    matches = pd.read_parquet(data_dir() / 'processed/matches.parquet')
    corners = pd.read_parquet(data_dir() / 'processed/corners.parquet')
    original = features(matches, corners)
    altered = corners.copy()
    altered.loc[altered.match_date >= '2016-03-01', 'shot_within_15s'] = True
    rebuilt = features(matches, altered)
    pd.testing.assert_frame_equal(original[original.match_date < '2016-03-01'], rebuilt[rebuilt.match_date < '2016-03-01'])
    assert (original.history_max_date < original.match_date).all()


def test_window_has_eight_and_excludes_cutoff():
    matches = pd.read_parquet(data_dir() / 'processed/matches.parquet')
    result = previous_matches(matches, 'Barcelona', '2016-03-01')
    assert len(result) == 8
    assert (result.match_date < '2016-03-01').all()
