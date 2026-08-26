from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class PairExclusion:
    subject_id: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class PairingResult:
    pairs: pd.DataFrame
    total_subjects: int
    paired_n: int
    exclusions: tuple[PairExclusion, ...]


def pair_pre_post(
    rows: pd.DataFrame,
    *,
    subject_column: str = "subject_id",
    session_column: str = "session",
    value_column: str = "metric_value",
    pre_label: str = "pre",
    post_label: str = "post",
) -> PairingResult:
    required = {subject_column, session_column, value_column}
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"Missing pairing columns: {', '.join(sorted(missing))}")
    subjects = tuple(dict.fromkeys(rows[subject_column].astype(str)))
    output: list[dict[str, object]] = []
    exclusions: list[PairExclusion] = []
    for subject in subjects:
        subject_rows = rows[rows[subject_column].astype(str) == subject]
        pre_values = pd.to_numeric(
            subject_rows.loc[subject_rows[session_column] == pre_label, value_column],
            errors="coerce",
        ).dropna()
        post_values = pd.to_numeric(
            subject_rows.loc[subject_rows[session_column] == post_label, value_column],
            errors="coerce",
        ).dropna()
        if len(pre_values) != 1 or len(post_values) != 1:
            exclusions.append(
                PairExclusion(
                    subject,
                    "E_PAIR_INCOMPLETE",
                    f"Expected one {pre_label} and one {post_label} finite value",
                )
            )
            continue
        row: dict[str, object] = {
            "subject_id": subject,
            "pre": float(pre_values.iloc[0]),
            "post": float(post_values.iloc[0]),
            "delta": float(post_values.iloc[0] - pre_values.iloc[0]),
        }
        if "group" in subject_rows.columns:
            groups = subject_rows["group"].dropna().astype(str).unique()
            if len(groups) == 1:
                row["group"] = groups[0]
        output.append(row)
    return PairingResult(pd.DataFrame(output), len(subjects), len(output), tuple(exclusions))


def difference_in_differences(
    pairs: pd.DataFrame,
    intervention_group: str,
    control_group: str,
) -> float:
    intervention = pd.to_numeric(
        pairs.loc[pairs["group"] == intervention_group, "delta"], errors="coerce"
    ).dropna()
    control = pd.to_numeric(
        pairs.loc[pairs["group"] == control_group, "delta"], errors="coerce"
    ).dropna()
    if intervention.empty or control.empty:
        return float("nan")
    return float(np.mean(intervention) - np.mean(control))
