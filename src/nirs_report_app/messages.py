"""Reader-facing wording shared by the charts, the Word report and the window."""

from __future__ import annotations

WARNING_TEXT = {
    "W_CHANNEL_MISSING": "有通道缺少資料",
    "W_CHANNEL_PARTIAL": "有通道只有部分資料有效",
    "W_CHANNEL_INVALID": "有通道資料無效",
    "W_ROI_DEGRADED": "區域內有效通道不足",
    "E_ROI_EMPTY": "區域內沒有有效通道",
    "W_LI_DENOMINATOR_SMALL": "左右訊號總和太小，LI 不穩定",
    "W_LI_OPPOSITE_SIGNS": "左右訊號方向相反，LI 需保守解讀",
    "E_LI_NONFINITE": "左右訊號含無效數值，無法計算 LI",
    "E_PAIR_INCOMPLETE": "缺少前測或後測，無法配對",
    "E_INSUFFICIENT_SAMPLE": "樣本數不足",
    "W_ZERO_VARIANCE": "數值沒有變異",
    "W_MODEL_CONVERGENCE": "統計模型未收斂",
}

DIRECTION_TEXT = {
    "left-dominant": "左側優勢",
    "right-dominant": "右側優勢",
    "bilateral": "雙側均衡",
}

ROI_TEXT = {
    "right_pfc": "右前額葉",
    "anterior_frontal": "前額中區",
    "left_pfc": "左前額葉",
    "lateral_frontal": "前額側區",
}


def describe_warning(code: str) -> str:
    """Return a readable sentence for a warning code, keeping the code for traceability."""
    text = WARNING_TEXT.get(code)
    return f"{text}（{code}）" if text else code


def describe_warnings(codes: tuple[str, ...]) -> str:
    return "；".join(describe_warning(code) for code in codes)


def roi_label(roi_id: str, fallback: str = "") -> str:
    """Chinese region name, followed by the stored English name when there is one."""
    chinese = ROI_TEXT.get(roi_id)
    if chinese is None:
        return fallback or roi_id.replace("_", " ")
    return f"{chinese} {fallback}".strip()
