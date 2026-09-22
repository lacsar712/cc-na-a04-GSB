from inspection.models import DeclineEvent, DeclineSetting


def judge(measured_cd: float, required_cd: float, bearing_error_deg: float) -> tuple[str, str]:
    if measured_cd < required_cd:
        return "不合格", "光强不足"
    if abs(bearing_error_deg) > 2:
        return "不合格", "方位偏差过大"
    return "合格", "光强与方位均在限内"


def decline_drop(prev_cd: float, curr_cd: float, threshold_cd: float) -> float | None:
    """比上一笔低出达到门槛即算走低，返回差额；否则 None。"""
    drop = round(prev_cd - curr_cd, 2)
    if drop > 0 and drop >= threshold_cd:
        return drop
    return None


def record_decline(prev, curr) -> DeclineEvent | None:
    """按当前门槛判定 curr 相对 prev 是否走低，走低则落一条走低事件。"""
    if prev is None:
        return None
    threshold = DeclineSetting.current().drop_cd
    drop = decline_drop(prev.measured_cd, curr.measured_cd, threshold)
    if drop is None:
        return None
    return DeclineEvent.objects.create(
        aid_code=curr.aid_code,
        prev_reading=prev,
        curr_reading=curr,
        threshold_cd=threshold,
        drop_cd=drop,
    )
