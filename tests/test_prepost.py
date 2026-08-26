import pandas as pd

from nirs_report_app.analysis.prepost import difference_in_differences, pair_pre_post


def test_pair_pre_post_calculates_post_minus_pre() -> None:
    rows = pd.DataFrame(
        [
            {"subject_id": "S01", "session": "pre", "metric_value": 1.0},
            {"subject_id": "S01", "session": "post", "metric_value": 4.0},
            {"subject_id": "S02", "session": "pre", "metric_value": 2.0},
            {"subject_id": "S02", "session": "post", "metric_value": 3.0},
        ]
    )

    result = pair_pre_post(rows)

    assert result.paired_n == 2
    assert result.exclusions == ()
    assert result.pairs.set_index("subject_id")["delta"].to_dict() == {"S01": 3.0, "S02": 1.0}


def test_pair_pre_post_excludes_incomplete_subject_without_filling_zero() -> None:
    rows = pd.DataFrame(
        [
            {"subject_id": "S01", "session": "pre", "metric_value": 1.0},
            {"subject_id": "S01", "session": "post", "metric_value": 2.0},
            {"subject_id": "S02", "session": "pre", "metric_value": 5.0},
        ]
    )

    result = pair_pre_post(rows)

    assert result.paired_n == 1
    assert result.total_subjects == 2
    assert result.exclusions[0].subject_id == "S02"
    assert result.exclusions[0].code == "E_PAIR_INCOMPLETE"
    assert "S02" not in result.pairs["subject_id"].tolist()


def test_difference_in_differences_uses_group_mean_changes() -> None:
    pairs = pd.DataFrame(
        {
            "group": ["intervention", "intervention", "control", "control"],
            "delta": [4.0, 2.0, 1.0, 1.0],
        }
    )
    assert difference_in_differences(pairs, "intervention", "control") == 2.0
