def judge(measured_cd: float, required_cd: float, bearing_error_deg: float) -> tuple[str, str]:
    if measured_cd < required_cd:
        return "不合格", "光强不足"
    if abs(bearing_error_deg) > 2:
        return "不合格", "方位偏差过大"
    return "合格", "光强与方位均在限内"


def decline_drop(prev_cd: float, curr_cd: float, threshold_cd: float) -> float | None:
    """本笔比上一笔低出达到门槛时返回差额，否则返回 None。"""
    drop = prev_cd - curr_cd
    if drop >= threshold_cd and drop > 0:
        return drop
    return None
