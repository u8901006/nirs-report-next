import warnings

import pandas as pd
import pytest

from nirs_report_app.analysis.regional import compare_regions


def test_regional_comparisons_include_all_pairs_and_holm_values() -> None:
    rows = []
    for subject, offset in (("S01", 0.0), ("S02", 0.2), ("S03", -0.1), ("S04", 0.1)):
        rows.extend(
            [
                {"subject_id": subject, "roi": "a", "metric_value": 3.0 + offset},
                {"subject_id": subject, "roi": "b", "metric_value": 2.0 + offset},
                {"subject_id": subject, "roi": "c", "metric_value": 1.0 + offset},
            ]
        )

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = compare_regions(pd.DataFrame(rows), ("a", "b", "c"), correction="holm")

    assert [f"{item.category.__name__}: {item.message}" for item in captured] == []
    assert len(result.contrasts) == 3
    assert {contrast.label for contrast in result.contrasts} == {"a - b", "a - c", "b - c"}
    assert all(contrast.adjusted_p_value is not None for contrast in result.contrasts)


def test_regional_comparison_rejects_derived_lateral_with_components() -> None:
    rows = pd.DataFrame(
        [
            {"subject_id": "S01", "roi": "left_pfc", "metric_value": 1.0},
            {"subject_id": "S01", "roi": "lateral_frontal", "metric_value": 1.0},
        ]
    )
    with pytest.raises(ValueError, match="derived lateral_frontal"):
        compare_regions(rows, ("left_pfc", "lateral_frontal"))
